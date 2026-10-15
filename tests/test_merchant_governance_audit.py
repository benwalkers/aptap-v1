"""Governance regression checks on the packaged synthetic sample."""
import csv
import json
from pathlib import Path

from categorise.core import MerchantCategoriser

ROOT = Path(__file__).resolve().parents[1]
DIR= ROOT/'outputs/merchant_governance'


def _csv(path):
    with path.open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))


def test_all_92_audited_and_reconciliation():
    audit=_csv(DIR/'merchant_audit_all_92.csv')
    assert len(audit)>=92
    assert len({r['description'] for r in audit})==len(audit)
    assert sum(int(r['transactions']) for r in audit)==sum(1 for _ in open(ROOT/'outputs/clean_transactions.csv',encoding='utf-8'))-1
    assert sum(r['existing_status']=='REVIEW_REQUIRED' for r in audit)>=21
    assert sum(r['proposed_status']=='REVIEW_EXISTING_ACCEPTANCE' for r in audit)==2


def test_no_unreviewed_auto_promotions():
    audit=_csv(DIR/'merchant_audit_all_92.csv')
    assert all(r['proposed_status']=='RETAIN_REVIEW' for r in audit if r['existing_status']=='REVIEW_REQUIRED')
    assert len(_csv(DIR/'merchant_review_proposals.csv'))==23


def test_proposed_registry_is_non_destructive():
    source=_csv(ROOT/'classification/curated_aliases.csv')
    proposed=_csv(DIR/'proposed_aliases_conservative.csv')
    removed={r['description'] for r in source}-{r['description'] for r in proposed}
    assert removed=={'ADMIRAL INS DD','ADMIRAL INSURANCE'}
    assert len(source)==len(proposed)+2
    r=MerchantCategoriser(ROOT/'data/merchant_labels.csv','lexical',aliases_path=DIR/'proposed_aliases_conservative.csv')
    assert r.classify('ADMIRAL INSURANCE').needs_review


def test_feature_impact_counts_consistent():
    d=json.loads((DIR/'scenario_impact.json').read_text())
    assert d['conservative']['bill_candidates'] <= d['baseline']['bill_candidates']
    assert d['conservative']['switch_candidates'] <= d['baseline']['switch_candidates']
    assert len(_csv(DIR/'scenario_removed_bills.csv'))==d['baseline']['bill_candidates']-d['conservative']['bill_candidates']
