"""End-to-end CLI, local incremental profile; no runtime network calls."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import resource
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

from categorise.core import MerchantCategoriser
from .ingest import ingest, input_files, declared_contract
from .features import features, csv_out
from .switch_validation import EVIDENCE_COLUMNS, validate_switches
from .bill_validation import EVIDENCE_COLUMNS as BILL_EVIDENCE_COLUMNS, validate_bills
from .report import make_report

ROOT=Path(__file__).resolve().parents[1]


def peak_mb():
    raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(raw/(1024*1024) if sys.platform=='darwin' else raw/1024,1)


def main(argv=None):
    p=argparse.ArgumentParser(description='ApTap Release 2: incremental ELT + ten-category selective offline categorisation')
    p.add_argument('data_dir',type=Path)
    p.add_argument('--as-of',default=None, help='Override source-month-end reporting date, YYYY-MM-DD')
    p.add_argument('--work-dir',type=Path,default=Path('work'))
    p.add_argument('--output-dir',type=Path,default=Path('outputs'))
    p.add_argument('--report-path',type=Path,default=Path('report/one_page_report.html'))
    p.add_argument('--bank-id',default='APTAP_SYNTHETIC')
    p.add_argument('--engine',choices=['auto','lexical','minilm'],default='lexical')
    p.add_argument('--model-path',type=Path,default=ROOT/'models/minilm')
    args=p.parse_args(argv)
    started=time.perf_counter()
    data=args.data_dir
    if args.as_of is None:
        # Bank delivery period, not last booking date (late postings are legitimate).
        periods=[period for f in input_files(data) for _,period in [declared_contract(f)]]
        latest=max(periods)
        year,month=map(int,latest.split('-'))
        import calendar
        as_of=dt.date(year,month,calendar.monthrange(year,month)[1])
    else:
        try:as_of=dt.date.fromisoformat(args.as_of)
        except ValueError as err:raise SystemExit(f'--as-of must be ISO date: {err}') from err
    effective_as_of=as_of.isoformat()
    if not (data/'merchant_labels.csv').exists():
        raise FileNotFoundError(f'Missing merchant_labels.csv in {data}')
    store,counters,batches=ingest(data,args.work_dir,args.bank_id)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(store) as conn:
        cols=['transaction_id','customer_id','booking_date','amount','description']
        rows=conn.execute('SELECT '+','.join(cols)+' FROM clean_transactions WHERE bank_id=? ORDER BY transaction_key',
                          (args.bank_id,))
        csv_out(args.output_dir/'clean_transactions.csv',cols,(dict(zip(cols,r)) for r in rows))
        cols=['source_file','source_line','transaction_id','reason','raw_json']
        rows=conn.execute('''SELECT r.source_file,r.source_line,r.transaction_id,r.reason,r.raw_json
             FROM rejected_rows r INNER JOIN ingestion_manifest m ON r.source_batch_id=m.batch_id
             WHERE m.bank_id=? ORDER BY m.source_file,m.source_sha256,r.source_line''',(args.bank_id,))
        csv_out(args.output_dir/'rejected_rows.csv',cols,(dict(zip(cols,r)) for r in rows))
        cols=['source_file','source_sha256','schema_version','source_period','rows','inserted','corrected','duplicates','invalid','conflicts','status','bronze_uri']
        rows=conn.execute('SELECT '+','.join(cols)+' FROM ingestion_manifest WHERE bank_id=? ORDER BY source_file,source_sha256',
                          (args.bank_id,))
        csv_out(args.output_dir/'raw_manifest.csv',cols,(dict(zip(cols,r)) for r in rows))
        clf=MerchantCategoriser(data/'merchant_labels.csv',args.engine,args.model_path,ROOT/'classification/curated_aliases.csv')
        # Additional evidence is opt-in to preserve the feature function interface.
        switch_evidence = []
        bills,switches,comparisons,review,method_counts,excluded=features(
            conn,clf,as_of,switch_evidence=switch_evidence,bank_id=args.bank_id)
        # Independent, read-only checks fail the run before publishing Gold outputs.
        bill_evidence, bill_validation = validate_bills(
            conn,clf,as_of,bills,bank_id=args.bank_id)
        switch_validation = validate_switches(
            conn,clf,as_of,switches,comparisons,switch_evidence,bank_id=args.bank_id)
        # Evaluate coverage against DISTINCT descriptions, not repeated payment rows.
        descriptors=[x[0] for x in conn.execute('SELECT DISTINCT description_key FROM clean_transactions WHERE bank_id=?',(args.bank_id,))]
        descriptor_counts=Counter(clf.classify(x).status for x in descriptors)
        unknown_transactions=conn.execute('SELECT description_key,COUNT(*) FROM clean_transactions WHERE bank_id=? GROUP BY description_key',(args.bank_id,)).fetchall()
        unknown_count=sum(n for d,n in unknown_transactions if clf.classify(d).needs_review)
    csv_out(args.output_dir/'recurring_bills.csv',
            ['customer_id','merchant','category','cadence','typical_amount','next_expected_date'],bills)
    csv_out(args.output_dir/'bill_evidence.csv',BILL_EVIDENCE_COLUMNS,bill_evidence)
    (args.output_dir/'bill_validation_summary.json').write_text(
        json.dumps(bill_validation,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    csv_out(args.output_dir/'switches.csv',
            ['customer_id','category','old_merchant','new_merchant','first_month_with_new'],switches)
    csv_out(args.output_dir/'switch_comparisons.csv',
            ['customer_id','category','old_merchant','new_merchant','old_amount','new_amount','saving','old_observations','new_observations','evidence'],comparisons)
    csv_out(args.output_dir/'switch_evidence.csv',EVIDENCE_COLUMNS,switch_evidence)
    (args.output_dir/'switch_validation_summary.json').write_text(
        json.dumps(switch_validation,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    csv_out(args.output_dir/'categorisation_review.csv',
            ['description','category','provider_id','method','score','needs_review','candidate_category','matched_reference','status'],
            [dict(description=r['description'],category=r['category'],provider_id=r['provider_id'] or '',method=r['method'],
                  score=r['score'],needs_review=r['needs_review'],candidate_category=r.get('candidate_category') or '',
                  matched_reference=r.get('matched_reference') or '',status=r['status']) for r in review])
    summaries=make_report(comparisons,args.report_path,effective_as_of,counters,switch_validation)
    metrics={**counters,'as_of':effective_as_of,'batch_actions':batches,
             'new_batches':sum(b['action']=='COMMITTED' for b in batches),
             'runtime_seconds':round(time.perf_counter()-started,3),'peak_memory_mb':peak_mb(),
             'recurring_bill_candidates':len(bills),'switch_candidates':len(switches),
             'switch_evidence_validation':switch_validation,
             'bill_evidence_validation':bill_validation,
             'review_descriptors_count':descriptor_counts.get('REVIEW_REQUIRED',0),
             'unknown_descriptors':descriptor_counts.get('REVIEW_REQUIRED',0),
             'total_unique_descriptors':len(descriptors),'unknown_transaction_count':unknown_count,
             'review_descriptors':len(review),'classification_methods':method_counts,
             'excluded_from_bill_features':excluded,
             'category_summary':[{'category':name,'pairs':count,'mean_observed_saving':round(mean,2),
                      'bootstrap_ci':list(ci) if ci else None,'provisional_pairs':provisional}
                     for name,count,mean,ci,provisional in summaries]}
    (args.output_dir/'run_metrics.json').write_text(json.dumps(metrics,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f"RECONCILIATION: {counters['raw']:,} = {counters['clean']:,} clean + {counters['rejected']:,} rejected")
    print(f"Batch actions: {[(x['file'],x['action']) for x in batches]}")
    print(f"Flagged for review: {metrics['unknown_descriptors']}/{metrics['total_unique_descriptors']} descriptors, {unknown_count:,} transaction occurrences")
    print(f"Bills (candidates): {len(bills):,}; switches (candidates): {len(switches):,}")
    print(f"Bill evidence verified: {bill_validation['validation_status']} | "
          f"{bill_validation['recurrence_evidence_counts']} | "
          f"monthly-total outliers: {bill_validation['bills_with_monthly_total_gap_gt_10pct']}")
    print(f"Switch evidence verified: {switch_validation['validation_status']} | "
          f"{switch_validation['evidence_counts']} | externally confirmed: 0")
    print(f"Runtime {metrics['runtime_seconds']}s; peak RSS {metrics['peak_memory_mb']} MiB")
    print(f"Outputs: {args.output_dir.resolve()} | report: {args.report_path}")

if __name__=='__main__':main()
