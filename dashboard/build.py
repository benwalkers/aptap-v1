"""Read-only source/booking month risk funnel and offline Plotly report.

Run after the governed merchant audit and scenario report. All PII-like customer
identifiers are kept out of the browser payload. Governance risk is qualitative.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from categorise.core import MerchantCategoriser

ROOT = Path(__file__).resolve().parents[1]
RISK_TIERS = ('high', 'medium', 'low_to_medium', 'unassessed')
MONTH_FIELDS = [
    'basis','month','active_clean','accepted','needs_review','accepted_high_risk',
    'high','medium','low_to_medium','unassessed','debit_volume_gbp',
    'review_debit_volume_gbp','high_risk_accepted_debit_volume_gbp',
    'review_rate_pct','acceptance_rate_pct',
]
MODEL_FIELDS = [
    'description','transactions','risk_tier','existing_status','accepted','needs_review',
    'final_category','lexical_category','lexical_score','minilm_category','minilm_score',
    'model_agreement','decision_group','additional_evidence_needed',
]
REVIEW_FIELDS = [
    'description','transactions','customers','risk_tier','accepted','needs_review',
    'decision_group','category','lexical_category','minilm_category','model_agreement',
    'debit_volume_gbp','additional_evidence_needed',
]


def rows_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as file:
        return list(csv.DictReader(file))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def _embed_json(data):
    # Stop merchant narratives or other source content breaking out of <script>.
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def produce(root=ROOT, *, with_minilm=False):
    root = Path(root)
    metrics = json.loads((root/'outputs/run_metrics.json').read_text(encoding='utf-8'))
    audit_list = rows_csv(root/'outputs/merchant_governance/merchant_audit_all_92.csv')
    audit = {row['description']:row for row in audit_list}
    scenario = json.loads((root/'outputs/merchant_governance/scenario_impact.json').read_text(encoding='utf-8'))
    clf = MerchantCategoriser(root/'data/merchant_labels.csv', engine='minilm' if with_minilm else 'lexical',
        model_path=root/'models/minilm', aliases_path=root/'classification/curated_aliases.csv')
    db = root/'work/incremental.sqlite'
    if not db.exists():
        raise FileNotFoundError(f'Missing {db}; run the pipeline first')
    conn = sqlite3.connect(f'file:{db.resolve()}?mode=ro', uri=True)
    try:
        raw_by_source = Counter(dict(conn.execute('''SELECT source_period,SUM(rows)
            FROM ingestion_manifest WHERE status='COMMITTED' GROUP BY source_period''')))
        rejected_by_source = Counter(dict(conn.execute('''SELECT m.source_period,COUNT(*)
            FROM rejected_rows r JOIN ingestion_manifest m ON r.source_batch_id=m.batch_id
            WHERE m.status='COMMITTED' GROUP BY m.source_period''')))
        # Use source_period for the ingestion funnel and booking_date for the financial lens.
        curs = conn.execute('''SELECT description_key,source_period,substr(booking_date,1,7),
            customer_id,amount FROM clean_transactions ORDER BY transaction_key''')
        stats = defaultdict(lambda: {'active_clean':0, 'accepted':0, 'needs_review':0,
            'accepted_high_risk':0, 'risk':Counter(), 'debit':Decimal('0'),
            'review_debit':Decimal('0'), 'high_accepted_debit':Decimal('0')})
        merchant = defaultdict(lambda: {'transactions':0, 'customers':set(), 'debit':Decimal('0')})
        total_desc = Counter()
        for desc, source_month, booking_month, customer, amount_str in curs:
            total_desc[desc] += 1
            a = audit.get(desc)
            accepted = bool(a and a.get('existing_status')=='ACCEPTED_DEMO')
            risk = a.get('risk_tier', 'unassessed') if a else 'unassessed'
            if risk not in RISK_TIERS:
                risk = 'unassessed'
            debit = max(Decimal('0'), -Decimal(amount_str))
            for basis, month in (('source',source_month),('booking',booking_month)):
                if not month:continue
                m = stats[(basis,month)]
                m['active_clean'] += 1
                m['accepted'] += int(accepted)
                m['needs_review'] += int(not accepted)
                m['accepted_high_risk'] += int(accepted and risk=='high')
                m['risk'][risk] += 1
                m['debit'] += debit
                if not accepted:m['review_debit'] += debit
                if accepted and risk=='high':m['high_accepted_debit'] += debit
                detail = merchant[(basis,month,desc)]
                detail['transactions'] += 1
                detail['customers'].add(customer)
                detail['debit'] += debit
        all_months = sorted(set(raw_by_source) | {m for b,m in stats} | set(rejected_by_source))
        rows = []
        details = {'source':{},'booking':{}}
        for basis in ('source','booking'):
            for month in all_months:
                s = stats[(basis,month)]
                n=s['active_clean']
                record = {
                    'basis':basis,'month':month,'active_clean':n,'accepted':s['accepted'],
                    'needs_review':s['needs_review'],'accepted_high_risk':s['accepted_high_risk'],
                    **{risk:s['risk'][risk] for risk in RISK_TIERS},
                    'debit_volume_gbp':str(s['debit'].quantize(Decimal('.01'))),
                    'review_debit_volume_gbp':str(s['review_debit'].quantize(Decimal('.01'))),
                    'high_risk_accepted_debit_volume_gbp':str(s['high_accepted_debit'].quantize(Decimal('.01'))),
                    'review_rate_pct':round(100*s['needs_review']/n,2) if n else 0,
                    'acceptance_rate_pct':round(100*s['accepted']/n,2) if n else 0,
                }
                if s['accepted'] + s['needs_review'] != n or sum(s['risk'].values()) != n:
                    raise ValueError(f'Classification-risk reconciliation failed: {basis} {month}')
                rows.append(record)
                record['debit_volume_gbp'] = float(s['debit'])
                record['review_debit_volume_gbp'] = float(s['review_debit'])
                record['high_risk_accepted_debit_volume_gbp'] = float(s['high_accepted_debit'])
                ds=[]
                for (b,m,d), item in merchant.items():
                    if b != basis or m != month:continue
                    a = audit.get(d, {})
                    ds.append({
                        'description':d,'transactions':item['transactions'],
                        'customers':len(item['customers']),
                        'debit_volume_gbp':float(item['debit']),
                        'risk_tier':a.get('risk_tier','unassessed'),
                        'accepted':a.get('existing_status')=='ACCEPTED_DEMO',
                        'review':a.get('existing_status')!='ACCEPTED_DEMO',
                        'category':a.get('existing_category',''),
                        'decision_group':a.get('decision_group','unassessed'),
                    })
                details[basis][month] = sorted(ds,key=lambda r:(-r['transactions'],r['description']))
        if sum(raw_by_source.values()) != metrics['raw']:
            raise ValueError('Manifest raw totals differ from pipeline metrics')
        if sum(rejected_by_source.values()) != metrics['rejected']:
            raise ValueError('Rejected source occurrences differ from pipeline metrics')
        if sum(stats[('source',m)]['active_clean'] for m in all_months) != metrics['clean']:
            raise ValueError('Source-attributed Silver count differs from pipeline metrics')
        # Per-source-period reconciliation holds for distinct occurrences, incl superseded rows.
        source_funnel={}
        for month in all_months:
            raw=raw_by_source[month]
            rejected=rejected_by_source[month]
            active=stats[('source',month)]['active_clean']
            source_funnel[month]={'raw':raw,'rejected':rejected,'active':active,
                                  'reconciliation_gap':raw-rejected-active}
        if sum(x['reconciliation_gap'] for x in source_funnel.values()) != 0:
            raise ValueError('Source funnel totals do not reconcile across periods')
    finally:
        conn.close()

    # Retrieval is diagnostic ONLY. A model score or model agreement never approves an alias.
    comparisons=[]
    for desc in sorted(total_desc):
        a=audit.get(desc,{})
        accepted=a.get('existing_status')=='ACCEPTED_DEMO'
        lex_cat,_,lex_score=clf._suggest_lexical(desc) if not accepted or a.get('risk_tier')=='high' else (None,None,None)
        sem = clf._suggest_semantic(desc) if with_minilm and (not accepted or a.get('risk_tier')=='high') else None
        agreement='AGREE' if sem is not None and sem[0]==lex_cat else 'DISAGREE' if sem is not None else 'NOT_RUN'
        comparisons.append({
            'description':desc,'transactions':total_desc[desc],
            'risk_tier':a.get('risk_tier','unassessed'),
            'existing_status':a.get('existing_status','UNASSESSED'),
            'accepted':accepted,'needs_review':not accepted,
            'final_category':a.get('existing_category',''),
            'lexical_category':lex_cat or '', 'lexical_score':lex_score if lex_score is not None else '',
            'minilm_category':sem[0] if sem else '',
            'minilm_score':round(float(sem[2]),5) if sem else '',
            'model_agreement':agreement,
            'decision_group':a.get('decision_group','unassessed'),
            'additional_evidence_needed':a.get('additional_evidence_needed',''),
        })
    # Merge global exposure with independent model observations for review priority.
    global_by_desc=defaultdict(lambda: {'customers':set(), 'debit':Decimal('0')})
    for (basis,month,desc), item in merchant.items():
        if basis!='source':continue
        global_by_desc[desc]['debit'] += item['debit']
        global_by_desc[desc]['customers'].update(item['customers'])
    priority=[]
    for row in comparisons:
        if not row['needs_review'] and row['risk_tier']!='high':continue
        d=global_by_desc[row['description']]
        priority.append({**row,'customers':len(d['customers']),
            'category':row['final_category'],
            'debit_volume_gbp':round(float(d['debit']),2)})
    priority.sort(key=lambda r:(not (r['accepted'] and r['risk_tier']=='high'),-r['transactions'],r['description']))

    comps=rows_csv(root/'outputs/switch_comparisons.csv')
    switches=rows_csv(root/'outputs/switches.csv')
    first_month={(r['customer_id'],r['category'],r['old_merchant'],r['new_merchant']):r['first_month_with_new'] for r in switches}
    commercial=defaultdict(lambda: {'comparisons':0,'lower':0,'total_difference':0.0})
    for x in comps:
        month=first_month.get((x['customer_id'],x['category'],x['old_merchant'],x['new_merchant']))
        if month is None:raise ValueError('Comparison does not match an emitted switch')
        key=(month,x['category'])
        c=commercial[key]
        c['comparisons']+=1
        c['lower']+=int(float(x['saving'])>0)
        c['total_difference']+=float(x['saving'])
    commercial_rows=[{'first_new_month':month,'category':cat,
        'comparisons':v['comparisons'],'lower_new':v['lower'],
        'share_lower_pct':round(100*v['lower']/v['comparisons'],2),
        'mean_difference_gbp':round(v['total_difference']/v['comparisons'],2)}
        for (month,cat),v in sorted(commercial.items())]
    if sum(r['comparisons'] for r in commercial_rows)!=metrics['switch_candidates']:
        raise ValueError('Commercial candidate reconciliation failed')

    directory=root/'outputs/dashboard'
    write_csv(directory/'monthly_classification_risk.csv',MONTH_FIELDS,rows)
    write_csv(directory/'model_comparison.csv',MODEL_FIELDS,comparisons)
    write_csv(directory/'review_priority.csv',REVIEW_FIELDS,priority)
    write_csv(directory/'commercial_candidate_months.csv',list(commercial_rows[0]) if commercial_rows else
        ['first_new_month','category','comparisons','lower_new','share_lower_pct','mean_difference_gbp'], commercial_rows)
    (directory/'policy_sensitivity.json').write_text(json.dumps(scenario,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    benchmark_path=root/'outputs/pr_evaluation/pr_evaluation_report.json'
    benchmark_models=json.loads(benchmark_path.read_text(encoding='utf-8')).get('models',[]) if benchmark_path.exists() else []
    payload={
        'benchmark': [{'model':r['model'], 'top1_accuracy':r['top1_accuracy'],
                        'top1_macro_f1':r['top1_macro_f1'],
                        'macro_average_precision':r['macro_average_precision']} for r in benchmark_models],
        'metadata':{'as_of':metrics['as_of'],'model_mode':'TF-IDF + MiniLM (diagnostic)' if with_minilm else 'TF-IDF only; MiniLM not run',
            'note':'Risk is a qualitative audit tier, NOT an ML confidence score. No unapproved model prediction is promoted.',
            'customer_privacy':'Only aggregated counts and merchant descriptions; no customer/transaction identifiers',
            'reporting_time':'Source-month funnel and selectable source/booking classification cohorts',
            'verified_savings':0,'externally_confirmed_switches':0},
        'months':all_months,'source_funnel':source_funnel,
        'classification':{b:{r['month']:r for r in rows if r['basis']==b} for b in ('source','booking')},
        'merchant_drilldown':details, 'model_comparison':comparisons,
        'review_priority':priority, 'policy':scenario, 'commercial':commercial_rows,
        'totals':{'raw':metrics['raw'],'clean':metrics['clean'],'rejected':metrics['rejected'],
                  'review':metrics['unknown_transaction_count'],'bill_candidates':metrics['recurring_bill_candidates'],
                  'switch_candidates':metrics['switch_candidates']},
    }
    vendor=root/'dashboard/vendor/plotly.min.js'
    if not vendor.is_file():
        raise FileNotFoundError(f'Offline Plotly.js missing: {vendor}. Apply the complete reporting patch.')
    template=(root/'dashboard/template.html').read_text(encoding='utf-8')
    if template.count('__EMBEDDED_PLOTLY__')!=1 or template.count('__DASHBOARD_DATA__')!=1:
        raise ValueError('Dashboard template placeholders invalid')
    body=template.replace('__EMBEDDED_PLOTLY__',vendor.read_text(encoding='utf-8'))
    body=body.replace('__DASHBOARD_DATA__',_embed_json(payload))
    output=root/'report/risk_dashboard.html'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(body,encoding='utf-8')
    print(f'DASHBOARD: {output} | {len(all_months)} months | {len(comparisons)} descriptors '
          f'| MiniLM diagnostics={with_minilm} | zero external resources')
    return payload
