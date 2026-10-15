"""Independent bill-evidence validation and bounded claims about recurring payments."""
import copy
import datetime as dt
import json
import sqlite3
from decimal import Decimal

import pytest

from categorise.core import Result
from pipeline.bill_validation import EVIDENCE_COLUMNS, validate_bills
from pipeline.features import features


class FixtureClassifier:
    @staticmethod
    def classify(description):
        trusted = description == 'ENERGY_COMPANY'
        return Result('energy', 'energy_co' if trusted else None,
                      'fixture', 1.0, not trusted, trusted, 'energy', description,
                      'ACCEPTED_DEMO' if trusted else 'REVIEW_REQUIRED')


def sample(rows):
    conn = sqlite3.connect(':memory:')
    conn.execute('''CREATE TABLE clean_transactions (
        bank_id TEXT, transaction_id TEXT, customer_id TEXT,
        booking_date TEXT, amount TEXT, description TEXT)''')
    conn.executemany('INSERT INTO clean_transactions VALUES (?,?,?,?,?,?)',rows)
    return conn


def row(tid,when,amount,description='ENERGY_COMPANY',bank='BANK_A',customer='C1'):
    return bank,tid,customer,when,str(amount),description


def run(conn, cutoff=dt.date(2026,9,30)):
    bills, *_ = features(conn,FixtureClassifier(),cutoff,bank_id='BANK_A')
    evidence, summary = validate_bills(conn,FixtureClassifier(),cutoff,bills,bank_id='BANK_A')
    return bills,evidence,summary


def test_two_months_full_lineage_and_expected_date():
    conn = sample([row('J1','2026-07-30','-20.00'),row('A1','2026-08-30','-30.00'),
                   row('S1','2026-09-30','-40.00')])
    bills,evidence,summary = run(conn)
    assert len(bills) == len(evidence) == 1
    assert list(bills[0]) == ['customer_id','merchant','category','cadence','typical_amount','next_expected_date']
    item=evidence[0]
    assert list(item) == EVIDENCE_COLUMNS
    assert item['recurrence_evidence']=='RECENT_CONSECUTIVE_MONTHS'
    assert item['next_expected_date']=='2026-10-30'
    assert json.loads(item['supporting_transaction_ids'])==['J1','A1','S1']
    assert json.loads(item['supporting_payment_amounts'])==['20.00','30.00','40.00']
    assert item['median_individual_payment']=='30.00'
    assert item['median_monthly_total']=='30.00'
    assert summary['validation_status']=='PASSED'
    assert summary['distinct_supporting_transaction_ids']==3
    assert summary['externally_verified_recurring_contracts']==0
    conn.close()


def test_same_day_same_amount_is_flagged_not_removed():
    conn=sample([row('A1','2026-08-14','-60'),row('A2','2026-08-14','-60'),
                 row('S1','2026-09-14','-60')])
    bills,evidence,summary=run(conn)
    assert bills[0]['typical_amount']=='60.00'
    assert evidence[0]['median_monthly_total']=='90.00'
    assert evidence[0]['monthly_total_gap_gt_10pct']=='true'
    assert evidence[0]['same_day_same_amount_groups']==1
    assert evidence[0]['same_day_same_amount_extra_payments']==1
    assert summary['bills_with_monthly_total_gap_gt_10pct']==1
    assert summary['bills_with_same_day_same_amount_payment_groups']==1
    conn.close()


def test_single_month_provisional_excludes_credit_untrusted_and_other_bank():
    conn=sample([row('S1','2026-09-22','-10.00'),
                 row('S2','2026-09-22','20.00'),
                 row('S3','2026-09-23','-80.00','UNTRUSTED'),
                 row('B1','2026-08-22','-90.00',bank='BANK_B')])
    bills,evidence,summary=run(conn)
    assert len(bills)==1
    assert evidence[0]['payment_count']==1
    assert evidence[0]['recurrence_evidence']=='MONTHLY_CANDIDATE_INSUFFICIENT_HISTORY'
    assert bills[0]['cadence']=='monthly_candidate'
    assert bills[0]['typical_amount']=='10.00'
    conn.close()


def test_historical_pair_not_misrepresented_as_recent():
    conn=sample([row('J1','2026-07-11','-10'),row('A1','2026-08-11','-10'),
                 row('O1','2026-10-11','-10')])
    _,evidence,_=run(conn,dt.date(2026,10,31))
    assert evidence[0]['cadence']=='monthly'
    assert evidence[0]['recent_consecutive_months']=='false'
    assert evidence[0]['recurrence_evidence']=='HISTORICAL_CONSECUTIVE_ONLY'
    conn.close()


@pytest.mark.parametrize('tamper', ['missing_bill','extra_bill','bad_cadence','bad_amount',
                                   'bad_date','duplicate_key'])
def test_validator_rejects_gold_tampering(tamper):
    conn=sample([row('A1','2026-08-14','-12.10'),row('S1','2026-09-14','-12.10')])
    bills,_,_=run(conn)
    modified=copy.deepcopy(bills)
    if tamper=='missing_bill': modified=[]
    elif tamper=='extra_bill': modified.append({**modified[0],'customer_id':'C99'})
    elif tamper=='bad_cadence': modified[0]['cadence']='monthly_candidate'
    elif tamper=='bad_amount': modified[0]['typical_amount']='999.99'
    elif tamper=='bad_date': modified[0]['next_expected_date']='2026-11-14'
    elif tamper=='duplicate_key': modified.append(modified[0].copy())
    with pytest.raises(ValueError,match='BILL_EVIDENCE_INVALID'):
        validate_bills(conn,FixtureClassifier(),dt.date(2026,9,30),modified,bank_id='BANK_A')
    conn.close()


def test_month_end_rollover_uses_last_valid_day():
    conn=sample([row('A1','2026-08-31','-20'),row('S1','2026-09-30','-20')])
    bills,_,_=run(conn)
    assert bills[0]['next_expected_date']=='2026-10-30'
    conn.close()


def test_current_month_must_be_present():
    conn=sample([row('A1','2026-08-14','-12.10')])
    bills,evidence,summary=run(conn)
    assert bills==[] and evidence==[]
    assert summary['candidate_count']==0
    conn.close()
