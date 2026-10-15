"""Traceable candidate evidence: never equate a payment pattern with proven switching."""
import copy
import datetime as dt
import json
import sqlite3
from pathlib import Path

import pytest

from categorise.core import Result
from pipeline.features import features
from pipeline.report import make_report
from pipeline.switch_validation import validate_switches


class VerifiedFixtureLabels:
    @staticmethod
    def classify(description):
        provider = {'OLD':'old_provider','NEW':'new_provider','UNTRUSTED':None}.get(description)
        return Result('energy',provider,'fixture',1.0,provider is None,
                      provider is not None,'energy',description,
                      'ACCEPTED_DEMO' if provider else 'REVIEW_REQUIRED')


def fixture(payments):
    conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE clean_transactions (bank_id TEXT, transaction_id TEXT, '
                 'customer_id TEXT, booking_date TEXT, amount TEXT, description TEXT)')
    conn.executemany('INSERT INTO clean_transactions VALUES (?,?,?,?,?,?)',
                     [('BANK_A',tid,'C42',date,amount,provider) for tid,date,amount,provider in payments])
    return conn


def calc(conn):
    reviewed=[]
    as_of=dt.date(2026,10,31)
    bills, switches, comps, review, counts, excluded = features(
        conn,VerifiedFixtureLabels(),as_of,switch_evidence=reviewed,bank_id='BANK_A')
    summary=validate_switches(conn,VerifiedFixtureLabels(),as_of,switches,comps,reviewed,bank_id='BANK_A')
    return bills,switches,comps,reviewed,summary


def test_two_months_both_sides_support_pattern_not_confirmation(tmp_path):
    conn=fixture([('o1','2026-07-11','-10','OLD'),('o2','2026-08-11','-20','OLD'),
                  ('n1','2026-09-11','-9','NEW'),('n2','2026-10-11','-11','NEW')])
    bills,switches,comps,evidence,summary=calc(conn)
    assert len(switches)==len(comps)==len(evidence)==1
    assert list(switches[0]) == ['customer_id','category','old_merchant','new_merchant','first_month_with_new']
    assert evidence[0]['evidence_level']=='SUPPORTED_PAYMENT_PATTERN'
    assert evidence[0]['externally_confirmed']=='false'
    assert evidence[0]['savings_verified']=='false'
    assert evidence[0]['old_month_count']==evidence[0]['new_month_count']==2
    assert json.loads(evidence[0]['old_transaction_ids']) == ['o1','o2']
    assert comps[0]['saving']==5.0
    assert summary['candidate_count']==1
    assert summary['externally_confirmed_switches']==0
    assert summary['verified_customer_savings']==0
    target=tmp_path/'report.html'
    make_report(comps,target,'2026-10-31',{'raw':4,'clean':4,'rejected':0},summary)
    html=target.read_text()
    assert '1</div>Supported payment patterns' in html
    assert '0</div>Externally confirmed' in html
    assert 'not confirmed switches' in html
    conn.close()


def test_two_new_payments_same_month_are_provisional():
    conn=fixture([('o1','2026-09-11','-20','OLD'),
                  ('n1','2026-10-11','-9','NEW'),('n2','2026-10-22','-11','NEW')])
    _,switches,comps,evidence,summary=calc(conn)
    assert len(switches)==1
    assert evidence[0]['new_payment_count']==2
    assert evidence[0]['new_month_count']==1
    assert evidence[0]['evidence_level']=='PROVISIONAL'
    assert comps[0]['evidence']=='provisional'
    assert summary['evidence_counts']['PROVISIONAL']==1
    conn.close()


@pytest.mark.parametrize('change', ['missing_reference','wrong_category','wrong_amount','date_mismatch',
                                    'fake_confirmation','fake_saving','wrong_level','wrong_pair'])
def test_validator_fails_closed_on_tampering(change):
    conn=fixture([('o1','2026-09-11','-20','OLD'),('n1','2026-10-11','-10','NEW')])
    _,switches,comps,evidence,summary=calc(conn)
    switches=copy.deepcopy(switches)
    comps=copy.deepcopy(comps)
    evidence=copy.deepcopy(evidence)
    if change=='missing_reference':evidence[0]['new_transaction_ids']=json.dumps(['missing'])
    if change=='wrong_category':evidence[0]['category']='mobile'
    if change=='wrong_amount':comps[0]['saving']=-99.0
    if change=='date_mismatch':evidence[0]['new_first_date']='2026-10-12'
    if change=='fake_confirmation':evidence[0]['externally_confirmed']='true'
    if change=='fake_saving':evidence[0]['savings_verified']='true'
    if change=='wrong_level':evidence[0]['evidence_level']='SUPPORTED_PAYMENT_PATTERN'
    if change=='wrong_pair':switches[0]['old_merchant']='other_provider'
    with pytest.raises(ValueError,match='SWITCH_EVIDENCE_INVALID'):
        validate_switches(conn,VerifiedFixtureLabels(),dt.date(2026,10,31),switches,comps,evidence,bank_id='BANK_A')
    conn.close()


def test_overlapping_providers_not_reported_as_switch():
    conn=fixture([('o1','2026-09-11','-20','OLD'),('o2','2026-10-11','-20','OLD'),
                  ('n1','2026-10-12','-10','NEW')])
    _,switches,comps,evidence,summary=calc(conn)
    assert not switches and not comps and not evidence
    assert summary['candidate_count']==0
    conn.close()


def test_untrusted_new_provider_is_excluded():
    conn=fixture([('o1','2026-09-11','-20','OLD'),('n1','2026-10-11','-10','UNTRUSTED')])
    _,switches,comps,evidence,summary=calc(conn)
    assert not switches and not comps and not evidence
    conn.close()


def test_validator_rejects_selectively_omitted_payment():
    conn=fixture([('o1','2026-08-11','-20','OLD'),('o2','2026-09-11','-20','OLD'),
                  ('n1','2026-10-11','-10','NEW')])
    _,switches,comps,evidence,_=calc(conn)
    evidence[0]['old_transaction_ids']=json.dumps(['o2'])
    with pytest.raises(ValueError,match='incomplete old provider evidence'):
        validate_switches(conn,VerifiedFixtureLabels(),dt.date(2026,10,31),switches,comps,evidence,bank_id='BANK_A')
    conn.close()


def test_validator_rejects_undisclosed_third_provider():
    conn=fixture([('o1','2026-09-11','-20','OLD'),('n1','2026-10-11','-10','NEW')])
    _,switches,comps,evidence,_=calc(conn)
    conn.execute("INSERT INTO clean_transactions VALUES ('BANK_A','third','C42','2026-10-12','-12','THIRD')")
    class ExtraProvider(VerifiedFixtureLabels):
        @staticmethod
        def classify(description):
            if description == 'THIRD':
                return Result('energy','third_provider','fixture',1.0,False,True,'energy',description,'ACCEPTED_DEMO')
            return VerifiedFixtureLabels.classify(description)
    with pytest.raises(ValueError,match='ambiguous third provider'):
        validate_switches(conn,ExtraProvider(),dt.date(2026,10,31),switches,comps,evidence,bank_id='BANK_A')
    conn.close()
