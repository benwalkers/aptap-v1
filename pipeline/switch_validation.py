"""Independent read-only checks of candidate switches against active canonical Silver.

Verification proves transaction-level traceability and rule consistency, NOT merchant
identity, contract cancellation, consumption-adjusted savings, or causal effects.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
from collections import Counter
from decimal import Decimal

from .features import month_of


EVIDENCE_COLUMNS = [
    'customer_id', 'category', 'old_merchant', 'new_merchant',
    'first_month_with_new', 'old_transaction_ids', 'new_transaction_ids',
    'old_booking_dates', 'new_booking_dates', 'old_month_count', 'new_month_count',
    'old_payment_count', 'new_payment_count', 'old_last_date', 'new_first_date',
    'new_last_date', 'gap_months', 'evidence_level', 'externally_confirmed',
    'savings_verified', 'amount_difference_status',
]
KEYS = ('customer_id', 'category', 'old_merchant', 'new_merchant')


def _require(condition, message):
    if not condition:
        raise ValueError('SWITCH_EVIDENCE_INVALID: ' + message)


def validate_switches(conn, classifier, as_of, switches, comparisons, evidence, bank_id=None):
    """Fail closed on missing IDs, altered rows, impossible time order, or false proof.

    Read the active Silver rows independently of the feature-building payment groups.
    The check does not use a merchant's text alone as external provider confirmation.
    """
    _require(len(switches) == len(comparisons) == len(evidence), 'unequal candidate counts')
    found = set()
    by_level = Counter()
    changes = Counter()
    all_involved_ids = set()
    for row in evidence:
        all_involved_ids.update(json.loads(row['old_transaction_ids']))
        all_involved_ids.update(json.loads(row['new_transaction_ids']))
    # Bulk lookups avoid a full table scan for every individual transaction_id;
    # the source Silver table is indexed by transaction_key, not transaction_id.
    # Keep below SQLite's conservative bind-variable limit for portability.
    silver_by_id = {}
    ordered_ids = sorted(all_involved_ids)
    for pos in range(0,len(ordered_ids),400):
        batch = ordered_ids[pos:pos+400]
        if not batch:
            continue
        placeholders = ','.join('?' for _ in batch)
        sql = ('SELECT transaction_id,customer_id,booking_date,amount,description '
               f'FROM clean_transactions WHERE transaction_id IN ({placeholders})')
        params = list(batch)
        if bank_id is not None:
            sql += ' AND bank_id=?'
            params.append(bank_id)
        for tid, customer, date, amount, description in conn.execute(sql,params):
            silver_by_id.setdefault(tid,[]).append((customer,date,amount,description))

    # Independently recover all trusted debits for every reported customer.
    # This detects selectively omitted payments and undisclosed third providers.
    involved_customers = sorted({row['customer_id'] for row in evidence})
    all_trusted = {}
    for pos in range(0,len(involved_customers),400):
        batch = involved_customers[pos:pos+400]
        if not batch:
            continue
        placeholders = ','.join('?' for _ in batch)
        sql = ('SELECT transaction_id,customer_id,booking_date,amount,description '
               f'FROM clean_transactions WHERE customer_id IN ({placeholders}) AND booking_date<=?')
        params = list(batch) + [as_of.isoformat()]
        if bank_id is not None:
            sql += ' AND bank_id=?'
            params.append(bank_id)
        for tid, customer, date, amount, description in conn.execute(sql,params):
            cls = classifier.classify(description)
            if Decimal(amount) < 0 and cls.usable_for_switches and not cls.needs_review and cls.provider_id:
                all_trusted.setdefault((customer,cls.category,cls.provider_id),set()).add(tid)

    for switch, comp, row in zip(switches, comparisons, evidence):
        key = tuple(row[k] for k in KEYS)
        _require(key not in found, f'duplicate candidate {key}')
        found.add(key)
        _require(key == tuple(comp[k] for k in KEYS) == tuple(switch[k] for k in KEYS), f'pair mismatch {key}')
        _require(row['first_month_with_new'] == switch['first_month_with_new'], f'month mismatch {key}')
        _require(row['externally_confirmed'] == 'false' and row['savings_verified'] == 'false',
                 f'unjustified confirmation or verified saving {key}')
        _require(row['amount_difference_status'] == 'OBSERVED_DIFFERENCE_ONLY', f'saving semantics {key}')
        old_ids = json.loads(row['old_transaction_ids'])
        new_ids = json.loads(row['new_transaction_ids'])
        _require(old_ids and new_ids, f'missing payment evidence {key}')
        _require(len(old_ids + new_ids) == len(set(old_ids + new_ids)), f'reused transaction IDs {key}')
        for side, ids in (('old',old_ids),('new',new_ids)):
            match = all_trusted.get((row['customer_id'],row['category'],row[f'{side}_merchant']),set())
            _require(set(ids) == match, f'incomplete {side} provider evidence {key}')
        providers = {provider for customer,category,provider in all_trusted
                     if customer == row['customer_id'] and category == row['category']}
        _require(providers == {row['old_merchant'],row['new_merchant']},
                 f'ambiguous third provider in category {key}')

        groups = []
        for label, ids in (('old', old_ids), ('new', new_ids)):
            pay = []
            for tid in ids:
                rows = silver_by_id.get(tid,[])
                _require(len(rows) == 1, f'{label} transaction {tid} missing or ambiguous {key}')
                customer, date, amount, description = rows[0]
                classification = classifier.classify(description)
                expected_provider = row[f'{label}_merchant']
                _require(customer == row['customer_id'] and classification.category == row['category']
                         and classification.provider_id == expected_provider
                         and classification.usable_for_switches and not classification.needs_review,
                         f'untrusted category/provider/customer for {tid}')
                pay_date = dt.date.fromisoformat(date)
                _require(pay_date <= as_of and Decimal(amount) < 0, f'ineligible payment {tid}')
                pay.append((pay_date, tid, abs(Decimal(amount))))
            pay.sort(key=lambda v:(v[0],v[1]))
            _require(ids == [p[1] for p in pay], f'{label} payment IDs not chronologically ordered {key}')
            _require(json.loads(row[f'{label}_booking_dates']) == [p[0].isoformat() for p in pay],
                     f'{label} payment dates inconsistent {key}')
            _require(len(pay) == int(row[f'{label}_payment_count']), f'{label} count mismatch {key}')
            _require(len({month_of(p[0]) for p in pay}) == int(row[f'{label}_month_count']),
                     f'{label} month count mismatch {key}')
            expected_med = statistics.median(p[2] for p in pay)
            _require(abs(float(expected_med)-float(comp[f'{label}_amount'])) <= 1e-6,
                     f'{label} median amount mismatch {key}')
            groups.append(pay)
        old, new = groups
        old_last = old[-1][0]
        new_first = new[0][0]
        new_last = new[-1][0]
        gap = month_of(new_first)-month_of(old_last)
        _require(1 <= gap <= 2, f'old/new gap outside permitted range {key}')
        _require(not ({month_of(p[0]) for p in old} & {month_of(p[0]) for p in new}),
                 f'overlap between provider billing months {key}')
        _require(month_of(new_last) == month_of(as_of), f'new merchant not current {key}')
        _require(row['old_last_date'] == old_last.isoformat()
                 and row['new_first_date'] == new_first.isoformat()
                 and row['new_last_date'] == new_last.isoformat()
                 and int(row['gap_months']) == gap
                 and row['first_month_with_new'] == new_first.strftime('%Y-%m'),
                 f'transition timeline mismatch {key}')
        months_old = len({month_of(p[0]) for p in old})
        months_new = len({month_of(p[0]) for p in new})
        level = ('SUPPORTED_PAYMENT_PATTERN' if months_old >= 2 and months_new >= 2
                 else 'REPEATED_NEW_PROVIDER' if months_new >= 2 else 'PROVISIONAL')
        _require(row['evidence_level'] == level, f'invalid evidence tier {key}')
        expected_old = statistics.median(p[2] for p in old)
        expected_new = statistics.median(p[2] for p in new)
        _require(abs(float(expected_old-expected_new)-float(comp['saving'])) <= 1e-6,
                 f'incorrect observed payment difference {key}')
        _require(comp['evidence'] == ('provisional' if months_new < 2 else 'repeated_new_provider'),
                 f'comparison tier mismatch {key}')
        by_level[level] += 1
        changes['lower_new_payment' if float(comp['saving']) > 0 else
                'higher_new_payment' if float(comp['saving']) < 0 else 'no_change'] += 1

    return {
        'validation_status':'PASSED',
        'candidate_count':len(evidence),
        'evidence_counts':{k:by_level[k] for k in
                           ('PROVISIONAL','REPEATED_NEW_PROVIDER','SUPPORTED_PAYMENT_PATTERN')},
        'externally_confirmed_switches':0,
        'verified_customer_savings':0,
        'observed_payment_difference_counts':{
            k:changes[k] for k in ('lower_new_payment','higher_new_payment','no_change')},
        'distinct_supporting_transaction_ids':len(all_involved_ids),
        'interpretation':('Candidate payment-pattern transitions only. Checked against active Silver IDs, dates, '
                          'provider/category mappings and medians; no independent contract cancellation '
                          'or verified savings evidence.'),
    }
