"""Employer-approved Release 2 contract: identity, GBP, ten classes, October month end."""
import csv
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from categorise.core import CATEGORIES, MerchantCategoriser
from categorise.__main__ import main as categorise_main
from pipeline.ingest import canonical, ingest

ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['transaction_id','customer_id','booking_date','amount','currency','description'])
        writer.writeheader()
        writer.writerows(rows)


def json_rec(tid, value, **kwargs):
    return dict(txn_id=tid,cust_ref='C1',posted='07/10/2026',value=value,
                direction='DEBIT',narrative='OCTOPUS ENERGY',**kwargs)


def test_gbp_input_variants_and_direction():
    for amount in ('1234.50', '1,234.50', '£1,234.50', 'GBP 1,234.50', '£ 1,234.50', '1,234.50 GBP'):
        result=canonical(json_rec('T1',amount),'jsonl_v2','BANK')
        assert result['amount']=='-1234.50'
        assert result['currency']=='GBP'
    r=json_rec('T2','£ 1,234.50');r['direction']='CREDIT'
    assert canonical(r,'jsonl_v2','BANK')['amount']=='1234.50'
    for invalid in ('-12.50','12,34.50','€12.50','1.234,50','NaN','5e5','12.345'):
        with pytest.raises(ValueError):canonical(json_rec('T1',invalid),'jsonl_v2','BANK')
    for invalid in ('USD','EUR'):
        with pytest.raises(ValueError,match='UNSUPPORTED_CURRENCY'):
            canonical(json_rec('T1','12.50',currency=invalid),'jsonl_v2','BANK')


def test_latest_valid_delivery_and_full_audit_chain(tmp_path):
    data=tmp_path/'data';data.mkdir()
    write_csv(data/'transactions_2026_07.csv',[
        dict(transaction_id='T1',customer_id='C1',booking_date='2026-07-04',amount='-10',currency='GBP',description='OCTOPUS ENERGY')])
    store=tmp_path/'work'
    ingest(data,store)
    later=[json_rec('T1','£ 20.00'),json_rec('T1','20.00'),json_rec('T1','25.00'),
           json_rec('T2','8.20',optional_bank_field='new'),json_rec('BAD','-8.00')]
    (data/'transactions_2026_10.jsonl').write_text('\n'.join(json.dumps(r) for r in later)+'\n')
    db,ct,acts=ingest(data,store)
    assert (ct['raw'],ct['clean'],ct['rejected'])==(6,2,4)
    assert (ct['corrected'],ct['superseded'],ct['duplicates'],ct['invalid'])==(2,2,1,1)
    assert sum(x['action']=='COMMITTED' for x in acts)==1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT amount FROM clean_transactions WHERE transaction_id='T1'").fetchone()[0]=='-25.00'
        assert conn.execute("SELECT COUNT(*) FROM transaction_corrections").fetchone()[0]==2
        assert conn.execute("SELECT COUNT(*) FROM rejected_rows WHERE reason='SUPERSEDED_BY_CORRECTION'").fetchone()[0]==2
        assert conn.execute("SELECT COUNT(*) FROM rejected_rows WHERE reason='DUPLICATE_TRANSACTION'").fetchone()[0]==1
        assert conn.execute("SELECT raw_json FROM rejected_rows WHERE reason='SUPERSEDED_BY_CORRECTION' LIMIT 1").fetchone()[0]
    db,ct2,acts=ingest(data,store)
    assert ct2==ct
    assert all(x['action']=='SKIPPED_IDENTICAL' for x in acts)


def test_invalid_replacement_does_not_destroy_active(tmp_path):
    data=tmp_path/'data';data.mkdir()
    write_csv(data/'transactions_2026_07.csv',[
        dict(transaction_id='T1',customer_id='C1',booking_date='2026-07-04',amount='-10',currency='GBP',description='OCTOPUS ENERGY')])
    ingest(data,tmp_path/'work')
    (data/'transactions_2026_10.jsonl').write_text(json.dumps(json_rec('T1','-22.00'))+'\n')
    db,ct,_=ingest(data,tmp_path/'work')
    assert ct['corrected']==0 and ct['invalid']==1
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT amount FROM clean_transactions').fetchone()[0]=='-10.00'


def test_categoriser_scoring_exactly_ten_and_review_flag(tmp_path):
    model=MerchantCategoriser(ROOT/'data/merchant_labels.csv','lexical',aliases_path=ROOT/'classification/curated_aliases.csv')
    for s in ('DIRECT LINE INS','AN UNSEEN BANK MERCHANT','CARD PAYMENT TO JOHN S','OCTOPUS ENERGY'):
        r=model.classify(s)
        assert r.category in CATEGORIES
        assert 'unknown'!=r.category
    assert model.classify('CARD PAYMENT TO JOHN S').needs_review
    assert not model.classify('CARD PAYMENT TO JOHN S').usable_for_switches
    assert not model.classify('OCTOPUS ENERGY').needs_review
    inp=tmp_path/'in.csv';out=tmp_path/'out.csv';rev=tmp_path/'review.csv'
    inp.write_text('description,reference\nCARD PAYMENT TO JOHN S,123\nOCTOPUS ENERGY,456\n')
    categorise_main([str(inp),str(out),'--engine','lexical','--labels',str(ROOT/'data/merchant_labels.csv'),
                     '--aliases',str(ROOT/'classification/curated_aliases.csv'), '--review-output',str(rev)])
    with out.open(newline='') as f:rows=list(csv.DictReader(f))
    assert rows[0]['category'] in CATEGORIES and rows[0]['needs_review']=='true'
    assert rows[1]['category']=='energy' and rows[1]['needs_review']=='false'
    assert rows[0]['reference']=='123'
    with rev.open(newline='') as f:review=list(csv.DictReader(f))
    assert len(review)==1 and review[0]['category'] in CATEGORIES


def test_reporting_date_defaults_latest_source_month(tmp_path):
    data=tmp_path/'data';data.mkdir()
    (data/'merchant_labels.csv').write_bytes((ROOT/'data/merchant_labels.csv').read_bytes())
    write_csv(data/'transactions_2026_07.csv',[
        dict(transaction_id='T1',customer_id='C1',booking_date='2026-07-04',amount='-10',currency='GBP',description='OCTOPUS ENERGY')])
    out=tmp_path/'out';work=tmp_path/'work';report=tmp_path/'report.html'
    cmd=[sys.executable,'-m','pipeline',str(data),'--engine','lexical','--work-dir',str(work),
         '--output-dir',str(out),'--report-path',str(report)]
    subprocess.run(cmd,check=True,cwd=ROOT,capture_output=True,text=True)
    assert json.loads((out/'run_metrics.json').read_text())['as_of']=='2026-07-31'
    # The newly received October source includes a July-dated resend: reporting
    # must use the declared October delivery period, not MAX(booking_date).
    (data/'transactions_2026_10.jsonl').write_text(json.dumps(json_rec('T1','10.00',source_platform='migration'))+'\n'+
                                                   json.dumps(json_rec('T2','13.50'))+'\n')
    subprocess.run(cmd,check=True,cwd=ROOT,capture_output=True,text=True)
    metrics=json.loads((out/'run_metrics.json').read_text())
    assert metrics['as_of']=='2026-10-31'
    assert metrics['clean']==2 and metrics['raw']==3 and metrics['rejected']==1
    assert len(list(csv.DictReader((out/'recurring_bills.csv').open())))>=1
    subprocess.run([*cmd,'--as-of','2026-09-30'],check=True,cwd=ROOT,capture_output=True,text=True)
    assert json.loads((out/'run_metrics.json').read_text())['as_of']=='2026-09-30'
