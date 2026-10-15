"""Reporting-only regression: integrity, policy boundaries, offline assets."""
import csv
import json
import sqlite3
from pathlib import Path

from dashboard.build import _embed_json, produce
from pipeline.report import make_report

ROOT=Path(__file__).resolve().parents[1]


def _csv(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def mini_fixture(tmp_path):
    for file in ('data/merchant_labels.csv','classification/curated_aliases.csv','dashboard/template.html'):
        dest=tmp_path/file
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((ROOT/file).read_bytes())
    asset=tmp_path/'dashboard/vendor/plotly.min.js'
    asset.parent.mkdir(parents=True,exist_ok=True)
    asset.write_text('window.Plotly={react:()=>{}};',encoding='utf-8')
    _csv(tmp_path/'outputs/merchant_governance/merchant_audit_all_92.csv',
        ['description','existing_status','risk_tier','existing_category','decision_group','additional_evidence_needed'],[
            {'description':'OCTOPUS ENERGY','existing_status':'ACCEPTED_DEMO', 'risk_tier':'low_to_medium',
             'existing_category':'energy','decision_group':'demo'},
            {'description':'CARD PAYMENT TO JOHN S','existing_status':'REVIEW_REQUIRED', 'risk_tier':'high',
             'existing_category':'water','decision_group':'payee_unknown'}])
    scenario={'as_of':'2026-09-30','baseline':{'bill_candidates':1,'switch_candidates':0},
              'conservative':{'bill_candidates':0,'switch_candidates':0}}
    (tmp_path/'outputs/merchant_governance/scenario_impact.json').write_text(json.dumps(scenario))
    metrics={'as_of':'2026-09-30','raw':4,'clean':3,'rejected':1,'switch_candidates':0,
             'recurring_bill_candidates':1,'unknown_transaction_count':1}
    (tmp_path/'outputs/run_metrics.json').write_text(json.dumps(metrics))
    _csv(tmp_path/'outputs/switch_comparisons.csv',
        ['customer_id','category','old_merchant','new_merchant','saving'],[])
    _csv(tmp_path/'outputs/switches.csv',
        ['customer_id','category','old_merchant','new_merchant','first_month_with_new'],[])
    db=tmp_path/'work/incremental.sqlite'
    db.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db) as conn:
        conn.executescript('''
         CREATE TABLE ingestion_manifest(batch_id TEXT,status TEXT,source_period TEXT,rows INTEGER);
         CREATE TABLE rejected_rows(source_batch_id TEXT);
         CREATE TABLE clean_transactions(transaction_key TEXT,description_key TEXT,source_period TEXT,
             booking_date TEXT,customer_id TEXT,amount TEXT);
        ''')
        conn.executemany('INSERT INTO ingestion_manifest VALUES (?,?,?,?)',[
            ('jul','COMMITTED','2026-07',1),('sep','COMMITTED','2026-09',3)])
        conn.execute('INSERT INTO rejected_rows VALUES (?)',('sep',))
        conn.executemany('INSERT INTO clean_transactions VALUES (?,?,?,?,?,?)',[
            ('a','OCTOPUS ENERGY','2026-07','2026-07-01','C1','-40.00'),
            ('b','CARD PAYMENT TO JOHN S','2026-09','2026-09-02','C2','-70.00'),
            ('c','OCTOPUS ENERGY','2026-09','2026-07-11','C1','-35.00')])
    return tmp_path


def test_dashboard_source_booking_risk_separation(tmp_path):
    root=mini_fixture(tmp_path)
    p=produce(root)
    source=p['classification']['source']['2026-09']
    booking=p['classification']['booking']['2026-09']
    assert p['source_funnel']['2026-09']=={'raw':3,'rejected':1,'active':2,'reconciliation_gap':0}
    assert source['active_clean']==2 and booking['active_clean']==1
    assert source['needs_review']==1 and source['high']==1
    assert source['accepted']==1 and source['accepted_high_risk']==0
    assert p['metadata']['model_mode']=='TF-IDF only; MiniLM not run'
    assert len(p['model_comparison'])==2
    assert all(x['model_agreement']=='NOT_RUN' for x in p['model_comparison'])
    dashboard=(root/'report/risk_dashboard.html').read_text()
    assert 'window.Plotly' in dashboard
    assert 'https://cdn.' not in dashboard
    assert '__DASHBOARD_DATA__' not in dashboard
    assert 'CARD PAYMENT TO JOHN S' in dashboard
    assert '"C1"' not in dashboard and '"C2"' not in dashboard


def test_dashboard_fails_on_reconciliation(tmp_path):
    import pytest
    root=mini_fixture(tmp_path)
    with sqlite3.connect(root/'work/incremental.sqlite') as c:
        c.execute("UPDATE ingestion_manifest SET rows=99 WHERE batch_id='sep'")
    with pytest.raises(ValueError, match='Manifest raw totals'):
        produce(root)


def test_safe_inline_json_and_no_external_assets():
    payload=_embed_json({'merchant':'</script><script>alert(1)</script>&'})
    assert '</script>' not in payload
    assert json.loads(payload)['merchant']=='</script><script>alert(1)</script>&'
    assert (ROOT/'dashboard/vendor/plotly.min.js').is_file()
    assert 'Plotly' in (ROOT/'dashboard/template.html').read_text()


def test_commercial_report_empty_and_negative(tmp_path):
    p=tmp_path/'commercial.html'
    make_report([],p,'2026-09-30',{'raw':0,'clean':0,'rejected':0})
    assert 'No provider-change candidates' in p.read_text()
    rows=[{'customer_id':'C1','category':'broadband','saving':-7.5,'evidence':'provisional'}]
    make_report(rows,p,'2026-09-30',{'raw':1,'clean':1,'rejected':0})
    text=p.read_text()
    assert '−£7.50' in text
    assert 'Insufficient sample' in text
    assert '<svg' in text
    assert 'Relative difference' not in text
