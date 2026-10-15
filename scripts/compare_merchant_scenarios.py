"""Read-only comparison of current and conservative demo registries against Silver CSV.

Does not update the source registry or incremental.sqlite, and does not ingest raw files.
Usage: python scripts/compare_merchant_scenarios.py
"""
from __future__ import annotations
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from categorise.core import MerchantCategoriser, canonical
from pipeline.features import features, csv_out


def load_clean_from_csv(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE clean_transactions ('
                 'transaction_id TEXT,customer_id TEXT,booking_date TEXT,amount TEXT,description TEXT)')
    with path.open(encoding='utf-8', newline='') as f:
        rows = csv.DictReader(f)
        buffer=[]
        for r in rows:
            buffer.append((r['transaction_id'],r['customer_id'],r['booking_date'],r['amount'],r['description']))
            if len(buffer) == 10000:
                conn.executemany('INSERT INTO clean_transactions VALUES (?,?,?,?,?)',buffer)
                buffer.clear()
        if buffer:
            conn.executemany('INSERT INTO clean_transactions VALUES (?,?,?,?,?)',buffer)
    conn.execute('CREATE INDEX idx_txid ON clean_transactions(transaction_id)')
    return conn


def key_bill(x):
    return (x['customer_id'],x['merchant'],x['category'])

def key_switch(x):
    return (x['customer_id'],x['category'],x['old_merchant'],x['new_merchant'],x['first_month_with_new'])


def run_scenario(conn, alias_path:Path, as_of):
    cl = MerchantCategoriser(ROOT/'data/merchant_labels.csv','lexical',aliases_path=alias_path)
    bills, switches, comparisons, review, counts, excluded = features(conn, cl, __import__('datetime').date.fromisoformat(as_of))
    return dict(bills=bills,switches=switches,comparisons=comparisons,review=review,
                methods=counts,excluded=excluded)


def main():
    report_dir = ROOT/'outputs/merchant_governance'
    proposals = report_dir/'proposed_aliases_conservative.csv'
    if not proposals.exists():
        raise FileNotFoundError(f'{proposals} missing; run scripts/audit_merchant_registry.py first')
    as_of=json.loads((ROOT/'outputs/run_metrics.json').read_text())['as_of']
    conn=load_clean_from_csv(ROOT/'outputs/clean_transactions.csv')
    baseline=run_scenario(conn,ROOT/'classification/curated_aliases.csv',as_of)
    scenario=run_scenario(conn,proposals,as_of)
    first_bills={key_bill(x) for x in baseline['bills']}
    second_bills={key_bill(x) for x in scenario['bills']}
    first_switches={key_switch(x) for x in baseline['switches']}
    second_switches={key_switch(x) for x in scenario['switches']}
    bill_removed=first_bills-second_bills
    bill_added=second_bills-first_bills
    switch_removed=first_switches-second_switches
    switch_added=second_switches-first_switches
    result={
        'as_of':as_of,
        'basis':'Scenario simulation on current clean transactions; no bank sign-off or source transaction changes',
        'baseline':{'bill_candidates':len(first_bills),'switch_candidates':len(first_switches),'review_descriptors':len(baseline['review'])},
        'conservative':{'bill_candidates':len(second_bills),'switch_candidates':len(second_switches),'review_descriptors':len(scenario['review'])},
        'delta':{'bill_candidates':len(second_bills)-len(first_bills),'switch_candidates':len(second_switches)-len(first_switches)},
        'removed':{'bill_candidates':len(bill_removed),'switch_candidates':len(switch_removed)},
        'added':{'bill_candidates':len(bill_added),'switch_candidates':len(switch_added)},
        'read_only':True,
        'proposed_change':'Demote two generic Admiral insurance aliases from demo-accepted car_insurance to unknown'
    }
    report_dir.mkdir(parents=True,exist_ok=True)
    (report_dir/'scenario_impact.json').write_text(json.dumps(result,indent=2)+'\n')
    csv_out(report_dir/'scenario_removed_bills.csv',
            ['customer_id','merchant','category'],
            [dict(zip(['customer_id','merchant','category'],v)) for v in sorted(bill_removed)])
    csv_out(report_dir/'scenario_removed_switches.csv',
            ['customer_id','category','old_merchant','new_merchant','first_month_with_new'],
            [dict(zip(['customer_id','category','old_merchant','new_merchant','first_month_with_new'],v)) for v in sorted(switch_removed)])
    print('BASELINE',result['baseline'])
    print('CONSERVATIVE',result['conservative'])
    print('DELTA',result['delta'])
    print('No source data or curated aliases modified.')
    conn.close()
    return result

if __name__=='__main__':
    main()
