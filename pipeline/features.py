"""Transparent month-level heuristics for current bills and candidate provider switches."""
from __future__ import annotations
import calendar
import csv
import datetime as dt
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


@dataclass
class Payment:
    customer: str
    provider: str
    category: str
    date: dt.date
    amount: Decimal
    description: str
    transaction_id: str


def month_of(date: dt.date):
    return date.year * 12 + date.month - 1


def next_month_date(date):
    year, month = date.year + (date.month == 12), (date.month % 12) + 1
    return date.replace(year=year, month=month, day=min(date.day, calendar.monthrange(year,month)[1]))


def features(conn, classifier, as_of, switch_evidence=None, bank_id=None):
    bill_payments = defaultdict(list)
    # Reading rows in stable order also makes any diagnostic samples reproducible.
    query = "SELECT transaction_id, customer_id, booking_date, amount, description FROM clean_transactions WHERE booking_date<=?"
    args = [as_of.isoformat()]
    if bank_id is not None:
        query += " AND bank_id=?"
        args.append(bank_id)
    query += " ORDER BY transaction_id"
    rejected_by_rule = 0
    classification_counts = defaultdict(int)
    review = {}
    for tid, customer, date, amount_str, description in conn.execute(query, args):
        result = classifier.classify(description)
        classification_counts[result.method] += 1
        if result.needs_review:
            review[description] = {"description":description,"category":result.category,
                                  "provider_id":result.provider_id or "","method":result.method,
                                  "score":result.score,"needs_review":result.needs_review, "candidate_category":result.candidate_category,
                                  "matched_reference":result.matched_reference, "status":result.status}
        amount = Decimal(amount_str)
        if amount >= 0 or result.category == "not_a_bill" or result.needs_review or not result.provider_id or not result.usable_for_switches:
            rejected_by_rule += 1
            continue
        entry = Payment(customer,result.provider_id,result.category,dt.date.fromisoformat(date),abs(amount),description,tid)
        bill_payments[(customer,result.category,result.provider_id)].append(entry)
    bills = []
    for (customer, category, provider), pay in sorted(bill_payments.items()):
        pay.sort(key=lambda p:(p.date,p.transaction_id))
        observed_months = sorted({month_of(p.date) for p in pay})
        if month_of(as_of) not in observed_months:
            continue
        latest = pay[-1]
        months = len(observed_months)
        # An end-of-month candidate with a single payment is INCLUDED but
        # explicitly marked candidate rather than inventing firm recurrence.
        cadence = "monthly" if months >= 2 and any(observed_months[i]-observed_months[i-1] == 1 for i in range(1,months)) else "monthly_candidate"
        typical = statistics.median(p.amount for p in pay)
        bills.append({"customer_id":customer,"merchant":provider,"category":category,
                      "cadence":cadence,"typical_amount":f"{typical:.2f}",
                      "next_expected_date":next_month_date(latest.date).isoformat()})
    # Switch: two distinct providers of SAME category, old last observed before
    # new first observed, new provider still observed in as-of month, and no
    # overlapping months. Still only observed replacement, not proven cancellation.
    by_customer_category = defaultdict(dict)
    for (customer,category,provider), pay in bill_payments.items():
        by_customer_category[(customer,category)][provider] = sorted(pay,key=lambda p:p.date)
    switches = []
    comparisons = []
    for (customer,category), providers in sorted(by_customer_category.items()):
        if len(providers) < 2: continue
        # Do not interpret concurrent products (two household contracts) as switches.
        items = sorted(providers.items(), key=lambda item:(item[1][0].date,item[0]))
        candidates = []
        for old_name, old_pay in items:
            for new_name, new_pay in items:
                if old_name == new_name: continue
                old_last_month = month_of(old_pay[-1].date)
                new_first_month = month_of(new_pay[0].date)
                new_last_month = month_of(new_pay[-1].date)
                if old_last_month >= new_first_month: continue
                if new_last_month != month_of(as_of): continue
                if new_first_month-old_last_month > 2: continue
                if any(month_of(p.date) >= new_first_month for p in old_pay): continue
                candidates.append((new_first_month,old_name,new_name,old_pay,new_pay))
        # Skip multi-provider ambiguous customers (potential overlapping services).
        if len(candidates) != 1 or len(providers) != 2:
            continue
        first,old_name,new_name,old_pay,new_pay = candidates[0]
        first_date = new_pay[0].date
        switches.append({"customer_id":customer,"category":category,
                         "old_merchant":old_name,"new_merchant":new_name,
                         "first_month_with_new":first_date.strftime("%Y-%m")})
        old_med = statistics.median(p.amount for p in old_pay)
        new_med = statistics.median(p.amount for p in new_pay)
        old_months = len({month_of(p.date) for p in old_pay})
        new_months = len({month_of(p.date) for p in new_pay})
        level = ("SUPPORTED_PAYMENT_PATTERN" if old_months >= 2 and new_months >= 2
                 else "REPEATED_NEW_PROVIDER" if new_months >= 2 else "PROVISIONAL")
        # Do not count two transactions in the same month as two separate monthly bills.
        comparisons.append({"customer_id":customer,"category":category,"old_merchant":old_name,
                            "new_merchant":new_name,"old_amount":float(old_med),"new_amount":float(new_med),
                            "saving":float(old_med-new_med),"old_observations":len(old_pay),
                            "new_observations":len(new_pay),
                            "evidence":"provisional" if new_months < 2 else "repeated_new_provider"})
        if switch_evidence is not None:
            switch_evidence.append({
                "customer_id":customer, "category":category,
                "old_merchant":old_name,"new_merchant":new_name,
                "first_month_with_new":first_date.strftime('%Y-%m'),
                "old_transaction_ids":json.dumps([p.transaction_id for p in old_pay]),
                "new_transaction_ids":json.dumps([p.transaction_id for p in new_pay]),
                "old_booking_dates":json.dumps([p.date.isoformat() for p in old_pay]),
                "new_booking_dates":json.dumps([p.date.isoformat() for p in new_pay]),
                "old_month_count":old_months,"new_month_count":new_months,
                "old_payment_count":len(old_pay),"new_payment_count":len(new_pay),
                "old_last_date":old_pay[-1].date.isoformat(),
                "new_first_date":new_pay[0].date.isoformat(),
                "new_last_date":new_pay[-1].date.isoformat(),
                "gap_months":month_of(new_pay[0].date)-month_of(old_pay[-1].date),
                "evidence_level":level,
                "externally_confirmed":"false",
                "savings_verified":"false",
                "amount_difference_status":"OBSERVED_DIFFERENCE_ONLY",
            })
    return bills, switches, comparisons, list(review.values()), dict(classification_counts), rejected_by_rule


def csv_out(path, columns, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8",newline="") as h:
        writer=csv.DictWriter(h,fieldnames=columns,extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    tmp.replace(path)
