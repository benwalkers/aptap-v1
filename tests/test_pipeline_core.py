import csv
import json
import sqlite3
from pathlib import Path

import pytest

from pipeline.ingest import canonical, connect, ingest, parse_date, stable_hash
from categorise.core import MerchantCategoriser

ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, rows):
    with path.open('w', newline='') as h:
        wr=csv.DictWriter(h,fieldnames=['transaction_id','customer_id','booking_date','amount','currency','description'])
        wr.writeheader();wr.writerows(rows)


def base():
    return {'transaction_id':'T100','customer_id':'C7','booking_date':'2026-07-01','amount':'-12.10',
            'currency':'GBP','description':'OCTOPUS ENERGY'}


def fixture(tmp_path):
    data=tmp_path/'input';data.mkdir()
    write_csv(data/'transactions_2026_07.csv',[base(),base()])
    return data,tmp_path/'work'


def test_date_schema_awareness():
    assert parse_date('2026-07-01','csv_v1')=='2026-07-01'
    assert parse_date('14/09/2026','jsonl_v2')=='2026-09-14'
    assert parse_date('2026-10-14','jsonl_v2')=='2026-10-14'
    with pytest.raises(ValueError,match='INVALID_BOOKING_DATE'):
        parse_date('07/09/2026','csv_v1')
    with pytest.raises(ValueError,match='INVALID_BOOKING_DATE'):
        parse_date('31/02/2026','jsonl_v2')


def test_key_stable_when_amount_and_date_change():
    record=base()
    one=canonical(record,'csv_v1','BANK_A')
    record.update(amount='-80.99',booking_date='2026-08-02')
    two=canonical(record,'csv_v1','BANK_A')
    assert one['transaction_key']==two['transaction_key']
    assert one['payload_hash']!=two['payload_hash']
    assert one['transaction_key']!=canonical(record,'csv_v1','BANK_B')['transaction_key']


def test_initial_reconciliation(tmp_path):
    data,work=fixture(tmp_path)
    path,counters,actions=ingest(data,work)
    assert counters=={'raw':2,'clean':1,'rejected':1,'duplicates':1,'invalid':0,'conflicts':0,'corrected':0,'superseded':0}
    assert actions[0]['action']=='COMMITTED'
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM rejected_rows').fetchone()[0]==1
        assert con.execute('SELECT status FROM ingestion_manifest').fetchone()[0]=='COMMITTED'
        assert Path(con.execute('SELECT bronze_uri FROM ingestion_manifest').fetchone()[0]).exists()


def test_same_files_rerun_skipped(tmp_path):
    data,work=fixture(tmp_path)
    _,before,_=ingest(data,work)
    _,after,actions=ingest(data,work)
    assert after==before
    assert actions[0]['action']=='SKIPPED_IDENTICAL'


def test_october_extra_fields_and_cross_month_replay(tmp_path):
    data,work=fixture(tmp_path)
    ingest(data,work)
    october=[{'txn_id':'T100','cust_ref':'C7','posted':'01/07/2026','value':'£12.10','direction':'DEBIT',
              'narrative':'octopus energy','new_optional_field':'extra'},
             {'txn_id':'T101','cust_ref':'C8','posted':'01/10/2026','value':'18.00','direction':'DEBIT',
              'narrative':'TESCO MOBILE','channel':'DIRECT_DEBIT'},
             {'txn_id':'T102','cust_ref':'C9','posted':'2026-10-02','value':'8.99','direction':'DEBIT',
              'narrative':'SPOTIFY','product_id':'xyz'}]
    path=data/'transactions_2026_10.jsonl'
    path.write_text('\n'.join(json.dumps(x) for x in october)+'\n')
    db,ct,events=ingest(data,work)
    assert ct['raw']==5 and ct['clean']==3 and ct['duplicates']==2
    assert [x for x in events if x['file'].endswith('10.jsonl')][0]['action']=='COMMITTED'
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT booking_date FROM clean_transactions WHERE transaction_id='T102'").fetchone()[0]=='2026-10-02'
        assert Path(con.execute("SELECT bronze_uri FROM ingestion_manifest WHERE source_file like '%10.jsonl'").fetchone()[0]).read_text().find('new_optional_field')>0


def test_corrected_resend_updates_silver_and_audits_superseded(tmp_path):
    data,work=fixture(tmp_path)
    ingest(data,work)
    october=[{'txn_id':'T100','cust_ref':'C7','posted':'01/07/2026','value':'999.99','direction':'DEBIT','narrative':'OCTOPUS ENERGY'}]
    (data/'transactions_2026_10.jsonl').write_text(json.dumps(october[0])+'\n')
    db,ct,_=ingest(data,work)
    assert ct['corrected']==1 and ct['clean']==1 and ct['rejected']==2 and ct['superseded']==1
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT amount FROM clean_transactions').fetchone()[0]=='-999.99'
        assert con.execute("SELECT COUNT(*) FROM rejected_rows WHERE reason='SUPERSEDED_BY_CORRECTION'").fetchone()[0]==1
        assert con.execute("SELECT COUNT(*) FROM transaction_corrections").fetchone()[0]==1


def test_invalid_json_and_missing_fields(tmp_path):
    data,work=fixture(tmp_path)
    (data/'transactions_2026_10.jsonl').write_text('{bad json\n'+json.dumps({'txn_id':'MISSING'})+'\n')
    _,ct,_=ingest(data,work)
    assert ct['invalid']==2 and ct['rejected']==3


def test_invalid_csv_header_loud_failure(tmp_path):
    data=tmp_path/'input';data.mkdir()
    (data/'transactions_2026_07.csv').write_text('transaction_id,customer_id\nT1,C1\n')
    with pytest.raises(ValueError,match='MISSING_CSV_HEADERS'):
        ingest(data,tmp_path/'work')


def test_source_name_replacement_detected(tmp_path):
    data,work=fixture(tmp_path)
    ingest(data,work)
    write_csv(data/'transactions_2026_07.csv',[base(),{**base(),'transaction_id':'T200'}])
    db,ct,events=ingest(data,work)
    assert ct['clean']==2 and ct['raw']==4
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM source_validation_events WHERE check_name='SOURCE_FILENAME_REUSED'").fetchone()[0]==1


def classifier():
    return MerchantCategoriser(ROOT/'data/merchant_labels.csv','lexical',aliases_path=ROOT/'classification/curated_aliases.csv')


def test_label_corrections_and_unknown():
    model=classifier()
    assert model.classify('TESCO MOBILE').category=='mobile'
    assert model.classify('OCTOPUS ENERGY').category=='energy'
    bad=model.classify('AVIVA DD')
    assert bad.category in __import__('categorise.core',fromlist=['CATEGORIES']).CATEGORIES and bad.needs_review and not bad.usable_for_switches
    assert model.classify('CARD PAYMENT TO JOHN S').needs_review


def test_unseen_description_does_not_force_bill():
    value=classifier().classify('NEBULA PAYMENT 1234')
    assert value.category in __import__('categorise.core',fromlist=['CATEGORIES']).CATEGORIES
    assert value.candidate_category is not None
    assert not value.usable_for_switches


def test_json_direction_safety():
    row={'txn_id':'T55','cust_ref':'C9','posted':'01/09/2026','value':'-12.00','direction':'DEBIT','narrative':'TESCO MOBILE'}
    with pytest.raises(ValueError,match='NEGATIVE_JSON_MAGNITUDE'):
        canonical(row,'jsonl_v2','BANK_A')
