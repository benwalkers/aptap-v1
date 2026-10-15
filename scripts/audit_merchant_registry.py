"""ApTap 92-descriptor merchant governance audit. Standard library; read-only inputs.

Produces proposals, NOT approved bank labels or ML probability estimates.
Usage: python scripts/audit_merchant_registry.py --output-dir outputs/merchant_governance
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from categorise.core import MerchantCategoriser, canonical

# These 21 cases are unresolved in Release 2. A source-name observation
# identifies a merchant or payee, not necessarily the product being billed.
REVIEW_CASES = {
    "CARD PAYMENT TO JOHN S": ("counterparty_unknown", "Water suggestion is unsupported; generic payee and highly variable card amounts", "Counterparty ID, MCC/payment-purpose evidence", "high"),
    "LIVERPOOL VICTORIA": ("insurance_product_unknown", "Insurer identity is plausible but no home/car policy identified", "Policy type or insurance product code", "high"),
    "DIRECT LINE INS": ("insurance_product_unknown", "Direct Line serves multiple insurance product lines", "Policy type or reference", "high"),
    "VIRGIN MEDIA": ("telecom_product_unknown", "Provider supplies bundled broadband, TV and other services", "Contract product code or approved broadband-only business rule", "medium"),
    "LV INSURANCE": ("insurance_product_unknown", "LV provides multiple insurance products; home subtype not established", "Policy type or reference", "high"),
    "AVIVA DD": ("insurance_product_unknown", "Aviva insurer name and DD do not distinguish car from home", "Policy type or reference", "high"),
    "AMZNPRIME UK": ("prime_bundled_product", "Prime membership includes multiple benefits; 'streaming' assignment is a policy decision", "Approved taxonomy mapping for bundled membership", "medium"),
    "AMAZON PRIME*": ("prime_bundled_product", "Prime membership is bundled rather than streaming-only", "Approved taxonomy mapping for bundled membership", "medium"),
    "DIRECTLINE DD": ("insurance_product_unknown", "Generic insurer DD; product subtype is not provided", "Policy type or reference", "high"),
    "AVIVA INSURANCE": ("insurance_product_unknown", "Generic insurer name; car insurance is an unverified assumption", "Policy type or reference", "high"),
    "BRITISH GAS SERVICES": ("service_product_unknown", "British Gas Services could be home services/cover, not energy supply", "Product/contract service code", "high"),
    "CROYDON COUNCIL": ("council_payment_unknown", "Local-authority payment does not explicitly say council tax", "Council-tax reference, payment scheme or service code", "medium"),
    "LV= DD": ("insurance_product_unknown", "Payee alias identifies likely insurer, not policy subtype", "Policy type or reference", "high"),
    "SKY DIGITAL": ("telecom_product_unknown", "Sky offers TV, broadband and other services; digital is not broadband-specific", "Product code or bank-verified rule", "medium"),
    "VIRGIN MEDIA PYMTS": ("telecom_product_unknown", "Payment recipient does not establish broadband service", "Product code or bank-verified rule", "medium"),
    "SKY UK LIMITED DD": ("telecom_product_unknown", "Payee and DD do not establish broadband product", "Product code or bank-verified rule", "medium"),
    "VIRGINMEDIA DD": ("telecom_product_unknown", "Direct debit identifies provider, not product", "Product code or bank-verified rule", "medium"),
    "BT GROUP PLC": ("telecom_product_unknown", "Generic telecom group descriptor; existing gym similarity is spurious", "Telecom product/payment reference", "high"),
    "SKY UK LTD": ("telecom_product_unknown", "Generic provider name, product not identifiable", "Product code or bank-verified rule", "medium"),
    "EE LIMITED": ("telecom_product_unknown", "EE offers mobile and broadband, so provider name alone is insufficient", "Product reference or bank-verified rule", "medium"),
    "VODAFONE LTD": ("telecom_product_unknown", "Vodafone provides mobile and broadband; no product specified", "Product reference or bank-verified rule", "medium"),
}

# These were accepted under synthetic-demo assumptions. Flag for product-level review;
# do not infer actual policies from merchant identity alone.
EXISTING_ACCEPTED_RISKS = {
    "ADMIRAL INS DD": ("insurance_product_unknown", "Admiral sells multiple insurance products; descriptor does not prove car insurance", "Policy type or product reference", "high"),
    "ADMIRAL INSURANCE": ("insurance_product_unknown", "Admiral sells multiple insurance products; descriptor does not prove car insurance", "Policy type or product reference", "high"),
}
CORRECTIONS = {
    "OCTOPUS ENERGY": ("broadband", "energy", "Merchant explicitly identifies an energy supplier"),
    "TESCO MOBILE": ("groceries", "mobile", "Descriptor explicitly identifies Tesco's mobile service"),
}

AUDIT_COLUMNS = [
    "description", "transactions", "customers", "booking_months", "first_booking_date", "last_booking_date",
    "human_label_raw", "reference_label_after_corrections", "existing_category", "existing_provider_id",
    "existing_status", "candidate_category", "candidate_score_lexical", "matched_reference",
    "proposed_category", "proposed_status", "decision_group", "risk_tier",
    "rationale", "additional_evidence_needed", "proposed_next_action", "source_label_correction",
]
REVIEW_COLUMNS = ["description", "transactions", "customers", "current_category", "candidate_category",
                  "proposed_category", "proposed_status", "decision_group", "risk_tier", "rationale", "additional_evidence_needed", "proposed_next_action"]


def write_csv(path: Path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def analyse(root: Path, output_dir: Path):
    labels_path = root / 'data/merchant_labels.csv'
    alias_path = root / 'classification/curated_aliases.csv'
    clean_path = root / 'outputs/clean_transactions.csv'
    if not all(x.exists() for x in (labels_path, alias_path, clean_path)):
        raise FileNotFoundError('Missing original label, alias or clean transactions CSV. Run ingestion first.')
    human = {}
    with labels_path.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            human[canonical(row['description'])] = row['category'].strip()
    curated = {}
    curated_rows = []
    with alias_path.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            row = dict(row)
            curated[canonical(row['description'])] = row
            curated_rows.append(row)
    clf = MerchantCategoriser(labels_path, engine='lexical', aliases_path=alias_path)
    occurrences = Counter()
    customers = defaultdict(set)
    months = defaultdict(set)
    first = {}
    last = {}
    with clean_path.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            d = canonical(row['description'])
            occurrences[d] += 1
            customers[d].add(row['customer_id'])
            booking = row['booking_date']
            months[d].add(booking[:7])
            first[d] = min(booking, first.get(d, booking))
            last[d] = max(booking, last.get(d, booking))
    # Additional month files may introduce new descriptors; do not impose 92 in October.
    # Review metadata for any new descriptors defaults to unverified rather than failing.
    audit = []
    for desc in sorted(occurrences):
        model = clf.classify(desc)
        current_category = model.category
        if desc in REVIEW_CASES:
            group, reason, evidence, risk = REVIEW_CASES[desc]
            proposed, status, next_action = model.category, 'RETAIN_REVIEW', 'REQUIRE_ADDITIONAL_CONTEXT'
        elif desc in EXISTING_ACCEPTED_RISKS:
            group, reason, evidence, risk = EXISTING_ACCEPTED_RISKS[desc]
            proposed, status, next_action = model.category, 'REVIEW_EXISTING_ACCEPTANCE', 'REVIEW_BEFORE_DEMOTION'
        elif model.needs_review:
            group, reason, evidence, risk = ('unseen_descriptor','No confirmed merchant-product mapping', 'Verify product reference', 'medium')
            proposed,status,next_action = model.category,'RETAIN_REVIEW','REQUIRE_ADDITIONAL_CONTEXT'
        else:
            group = 'existing_curated_demo'
            reason = 'Retain existing demo mapping as a provisional reference; no independent bank review supplied'
            evidence = 'Bank-reviewed alias or source-product evidence before production approval'
            risk = 'low_to_medium'
            proposed, status, next_action = current_category, 'RETAIN_DEMO_MAPPING', 'KEEP_DEMO_ONLY'
        corrected = CORRECTIONS.get(desc)
        audit.append({
            'description': desc, 'transactions': occurrences[desc], 'customers': len(customers[desc]),
            'booking_months': '|'.join(sorted(months[desc])), 'first_booking_date': first[desc],
            'last_booking_date': last[desc], 'human_label_raw': human.get(desc, ''),
            'reference_label_after_corrections': clf.labels.get(desc, ''),
            'existing_category': current_category, 'existing_provider_id': model.provider_id or '',
            'existing_status': model.status, 'candidate_category': model.candidate_category or '',
            'candidate_score_lexical': '' if model.score is None else model.score,
            'matched_reference': model.matched_reference or '', 'proposed_category': proposed,
            'proposed_status': status, 'decision_group': group, 'risk_tier': risk,
            'rationale': reason, 'additional_evidence_needed': evidence,
            'proposed_next_action': next_action,
            'source_label_correction': f'{corrected[0]} -> {corrected[1]}' if corrected else '',
        })
    reviewed = [r for r in audit if r['proposed_status'] != 'RETAIN_DEMO_MAPPING']
    reviewed.sort(key=lambda x:(0 if x['proposed_status']=='REVIEW_EXISTING_ACCEPTANCE' else 1,
                                -int(x['transactions']), x['description']))
    directory = output_dir
    write_csv(directory/'merchant_audit_all_92.csv', AUDIT_COLUMNS, audit)
    review_rows = [{
        'description':r['description'], 'transactions':r['transactions'], 'customers':r['customers'],
        'current_category':r['existing_category'], 'candidate_category':r['candidate_category'],
        'proposed_category':r['proposed_category'], 'proposed_status':r['proposed_status'],
        'decision_group':r['decision_group'], 'risk_tier':r['risk_tier'], 'rationale':r['rationale'],
        'additional_evidence_needed':r['additional_evidence_needed'],
        'proposed_next_action':r['proposed_next_action'],
    } for r in reviewed]
    write_csv(directory/'merchant_review_proposals.csv', REVIEW_COLUMNS, review_rows)
    write_csv(directory/'merchant_label_corrections.csv',
              ['description','original_label','corrected_label','reason','status'],
              [{ 'description': d, 'original_label': before, 'corrected_label': after, 'reason':why,
                  'status':'CORRECTION_ALREADY_APPLIED_IN_RELEASE1' }
               for d,(before,after,why) in sorted(CORRECTIONS.items())])
    # Non-destructive scenario to test the impact of removing 2 weak insurance mappings.
    conservative = [r for r in curated_rows if canonical(r['description']) not in EXISTING_ACCEPTED_RISKS]
    write_csv(directory/'proposed_aliases_conservative.csv',
              ['description','category','provider_id','review_status','evidence'], conservative)
    unknown = [r for r in audit if r['existing_status']=='REVIEW_REQUIRED']
    risks = [r for r in audit if r['proposed_status']=='REVIEW_EXISTING_ACCEPTANCE']
    summary = {
        'audit_schema_version': '1.0', 'source': 'Release 2 clean_transactions.csv and existing merchant catalogues',
        'observed_on': 'source_snapshot',
        'total_unique_descriptors':len(audit), 'total_clean_transactions':sum(occurrences.values()),
        'current_demo_accepted_descriptors':len(audit)-len(unknown),
        'current_unknown_descriptors':len(unknown),
        'current_unknown_transactions':sum(int(r['transactions']) for r in unknown),
        'additional_accepted_aliases_flagged':len(risks),
        'additional_accepted_alias_transactions_at_risk':sum(int(r['transactions']) for r in risks),
        'conservative_scenario_unknown_descriptors':len(unknown)+len(risks),
        'conservative_scenario_unknown_transactions':sum(int(r['transactions']) for r in unknown+risks),
        'new_auto_approvals': 0,
        'notes': [
            'No additional merchant type is accepted from ML similarity or manufacturer/provider identity alone.',
            'All mappings marked CURATED_DEMO are synthetic assumptions; none establishes external bank sign-off.',
            'Two already-applied human-label corrections are preserved with original source-label provenance.',
            'Proposed conservative registry removes only the two generic Admiral insurance aliases; it is NOT automatically deployed.',
            'Savings and switching results must be rerun and checked before production promotion.'
        ]
    }
    (directory/'merchant_governance_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(f"AUDITED {len(audit)} descriptors, {summary['total_clean_transactions']:,} clean transactions")
    print(f"REVIEW REQUIRED {len(unknown)} descriptions / {summary['current_unknown_transactions']:,} transaction occurrences")
    print(f"ADDITIONAL RISK {len(risks)} accepted demo mappings / {summary['additional_accepted_alias_transactions_at_risk']:,} transactions")
    print(f"CONSERVATIVE PROPOSAL {summary['conservative_scenario_unknown_descriptors']} review-required / {summary['conservative_scenario_unknown_transactions']:,} transactions")
    print(f"NO NEW AUTO-APPROVALS. Proposals written to {directory}")
    return summary

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir',default='outputs/merchant_governance', type=Path)
    opts=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    analyse(root, opts.output_dir)
