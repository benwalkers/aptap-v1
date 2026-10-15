"""Independent recurring-bill audit against active, bank-scoped Silver transactions.

The validator checks feature completeness and arithmetic without modifying transactions,
merging suspicious payments, or claiming that a recurring contract was verified.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
from collections import Counter, defaultdict
from decimal import Decimal

from .features import month_of, next_month_date


EVIDENCE_COLUMNS = [
    'customer_id', 'merchant', 'category', 'cadence', 'typical_amount',
    'next_expected_date', 'supporting_transaction_ids', 'supporting_booking_dates',
    'supporting_payment_amounts', 'payment_count', 'distinct_month_count',
    'observed_months', 'reporting_month_present', 'consecutive_month_pair',
    'recent_consecutive_months', 'recurrence_evidence', 'first_booking_date',
    'last_booking_date', 'multi_payment_months',
    'same_day_same_amount_groups', 'same_day_same_amount_extra_payments',
    'median_individual_payment', 'median_monthly_total',
    'monthly_total_gap_pct', 'monthly_total_gap_gt_10pct',
    'amount_semantics', 'externally_verified',
]
BILL_KEYS = ('customer_id', 'merchant', 'category')


def _require(condition, message):
    if not condition:
        raise ValueError('BILL_EVIDENCE_INVALID: ' + message)


def validate_bills(conn, classifier, as_of, bills, bank_id=None):
    """Recompute evidence from Silver; fail closed on inconsistent Gold candidate rows.

    Return (audit rows, summary). The report should use *median individual payment*,
    while median monthly provider expenditure is separately shown as a diagnostic.
    """
    reported = {}
    for row in bills:
        key = (row['customer_id'], row['merchant'], row['category'])
        _require(key not in reported, f'duplicate bill key {key}')
        reported[key] = row

    args = [as_of.isoformat()]
    sql = ('SELECT transaction_id, customer_id, booking_date, amount, description '
           'FROM clean_transactions WHERE booking_date<=?')
    if bank_id is not None:
        sql += ' AND bank_id=?'
        args.append(bank_id)
    sql += ' ORDER BY booking_date,transaction_id'

    trusted = defaultdict(list)
    observed_ids = set()
    for tid, customer, date_text, signed_amount, description in conn.execute(sql,args):
        amount = Decimal(signed_amount)
        if amount >= 0:
            continue
        result = classifier.classify(description)
        if (result.category == 'not_a_bill' or result.needs_review or
                not result.provider_id or not result.usable_for_switches):
            continue
        _require(tid not in observed_ids, f'ambiguous/repeated trusted transaction ID {tid}')
        observed_ids.add(tid)
        date = dt.date.fromisoformat(date_text)
        trusted[(customer,result.provider_id,result.category)].append(
            (date,tid,-amount,description))

    current_month = month_of(as_of)
    expected_keys = {
        k for k,payments in trusted.items()
        if any(month_of(p[0]) == current_month for p in payments)
    }
    _require(set(reported) == expected_keys,
             'bill keys do not match eligible reporting-month providers; '
             f'missing={len(expected_keys - set(reported))}, unexpected={len(set(reported) - expected_keys)}')

    evidence=[]
    counter=Counter()
    for key,row in sorted(reported.items()):
        payments = sorted(trusted[key], key=lambda p:(p[0],p[1]))
        dates = [p[0] for p in payments]
        months = sorted({month_of(day) for day in dates})
        by_month = defaultdict(list)
        repeated_exact = Counter()
        for day,tid,amount,description in payments:
            by_month[month_of(day)].append(amount)
            repeated_exact[(day,amount,description)] += 1
        multi_months = sum(len(v)>1 for v in by_month.values())
        repeated_groups = sum(n>1 for n in repeated_exact.values())
        repeated_extra = sum(n-1 for n in repeated_exact.values() if n>1)
        any_pair = any(right-left==1 for left,right in zip(months,months[1:]))
        recent_pair = current_month-1 in months and current_month in months
        expected_cadence = 'monthly' if len(months)>=2 and any_pair else 'monthly_candidate'
        individual_median = statistics.median(p[2] for p in payments)
        monthly_median = statistics.median(sum(group) for group in by_month.values())
        gap = abs(individual_median - monthly_median) / monthly_median if monthly_median else Decimal(0)
        forecast = next_month_date(dates[-1]).isoformat()
        _require(row['cadence'] == expected_cadence, f'cadence mismatch {key}')
        _require(Decimal(row['typical_amount']) == Decimal(f'{individual_median:.2f}'),
                 f'typical amount mismatch {key}')
        _require(row['next_expected_date'] == forecast, f'forecast date mismatch {key}')
        _require(month_of(dates[-1]) == current_month, f'missing current-month payment {key}')
        _require(individual_median > 0, f'nonpositive amount {key}')
        if recent_pair:
            tier = 'RECENT_CONSECUTIVE_MONTHS'
        elif expected_cadence == 'monthly':
            tier = 'HISTORICAL_CONSECUTIVE_ONLY'
        else:
            tier = 'MONTHLY_CANDIDATE_INSUFFICIENT_HISTORY'
        evidence.append({
            'customer_id':key[0], 'merchant':key[1], 'category':key[2],
            'cadence':expected_cadence, 'typical_amount':row['typical_amount'],
            'next_expected_date':forecast,
            'supporting_transaction_ids':json.dumps([p[1] for p in payments]),
            'supporting_booking_dates':json.dumps([p[0].isoformat() for p in payments]),
            'supporting_payment_amounts':json.dumps([str(p[2]) for p in payments]),
            'payment_count':len(payments), 'distinct_month_count':len(months),
            'observed_months':json.dumps([f'{(m//12):04d}-{(m%12)+1:02d}' for m in months]),
            'reporting_month_present':'true',
            'consecutive_month_pair':str(any_pair).lower(),
            'recent_consecutive_months':str(recent_pair).lower(),
            'recurrence_evidence':tier,
            'first_booking_date':dates[0].isoformat(), 'last_booking_date':dates[-1].isoformat(),
            'multi_payment_months':multi_months,
            'same_day_same_amount_groups':repeated_groups,
            'same_day_same_amount_extra_payments':repeated_extra,
            'median_individual_payment':f'{individual_median:.2f}',
            'median_monthly_total':f'{monthly_median:.2f}',
            'monthly_total_gap_pct':f'{gap*100:.4f}',
            'monthly_total_gap_gt_10pct':str(gap>Decimal('0.10')).lower(),
            'amount_semantics':'MEDIAN_INDIVIDUAL_PAYMENT_NOT_MONTHLY_SPEND',
            'externally_verified':'false',
        })
        counter[tier]+=1
        counter['supporting_payments']+=len(payments)
        if multi_months:
            counter['bills_with_multiple_payments_in_any_month']+=1
        if repeated_groups:
            counter['bills_with_same_day_same_amount_payment_groups']+=1
            counter['same_day_same_amount_payment_groups']+=repeated_groups
            counter['same_day_same_amount_extra_payments']+=repeated_extra
        if gap>Decimal('0.10'):
            counter['bills_with_monthly_total_gap_gt_10pct']+=1

    return evidence, {
        'validation_status':'PASSED',
        'as_of':as_of.isoformat(),
        'candidate_count':len(bills),
        'cadence_counts':dict(sorted(Counter(r['cadence'] for r in bills).items())),
        'recurrence_evidence_counts':{
            k:counter[k] for k in ('RECENT_CONSECUTIVE_MONTHS',
                                    'HISTORICAL_CONSECUTIVE_ONLY',
                                    'MONTHLY_CANDIDATE_INSUFFICIENT_HISTORY')},
        'distinct_supporting_transaction_ids':counter['supporting_payments'],
        'bills_with_multiple_payments_in_any_month':counter['bills_with_multiple_payments_in_any_month'],
        'bills_with_same_day_same_amount_payment_groups':counter['bills_with_same_day_same_amount_payment_groups'],
        'same_day_same_amount_payment_groups':counter['same_day_same_amount_payment_groups'],
        'same_day_same_amount_extra_payments':counter['same_day_same_amount_extra_payments'],
        'bills_with_monthly_total_gap_gt_10pct':counter['bills_with_monthly_total_gap_gt_10pct'],
        'externally_verified_recurring_contracts':0,
        'interpretation':('Every current-month bill candidate checked against active Silver IDs, trust rules, '
                           'recurrence, individual-payment medians and forecast dates. Same-day repeats '
                           'are flagged, never silently deleted. Monthly totals are diagnostic only; '
                           'no contractual recurrence or future charge is externally verified.'),
    }
