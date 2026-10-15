# Recurring-bill evidence validation — additional Release 2 quality gate

The employer-scored `outputs/recurring_bills.csv` remains unchanged: `customer_id, merchant, category, cadence, typical_amount, next_expected_date`.

## What is checked

`pipeline/bill_validation.py` is called automatically by `python -m pipeline data/` **after** candidate feature construction and **before** publication of Gold CSV outputs. It independently scans bank-scoped active Silver rows through the reporting cutoff; verifies which debit payments are trusted for business features; and checks the **complete** set of current-month customer–provider–category bill keys. For each bill it verifies payment IDs, number and dates of observations, cadence, median *individual* payment amount, and next expected date. Missing/duplicated bill keys, wrong amounts, wrong cadence, or inaccurate forecasts raise `BILL_EVIDENCE_INVALID` and stop publishing Gold outputs. The engine's classification acceptance policy is not changed by this check.

**Important semantics:** `typical_amount` is a median of *individual observed debit payments* to the accepted provider, not monthly total spend. Same-day, same-amount transactions with different bank transaction IDs are **not silently merged or removed**: they are flagged in separate evidence fields. `next_expected_date` is an estimated next-payment date and does not prove an active bank mandate or subscription. `monthly` means the history includes a pair of consecutive payment months; the evidence file separately distinguishes consecutive months immediately preceding the report cutoff from historical-only consecutive months.

## Supplemental audit outputs

- `outputs/bill_evidence.csv` — transaction ID, booking date and amount arrays; observed months; recent-vs-historical recurrence; same-day repeated-payment groups; count of months with multiple payments; median monthly provider total for *comparison only*; relative difference between that monthly median and `typical_amount`.
- `outputs/bill_validation_summary.json` — validation status; number of candidates and supporting payment IDs; cadence and evidence tier counts; count of repeated-payment groups; >10% individual-vs-monthly median differences; explicit count of **zero externally verified recurring contracts**.
- `outputs/run_metrics.json` — embeds the same `bill_evidence_validation` summary.

All supplemental audit rows are diagnostic: suspected repeated payments should be investigated using bank-provided identifiers or processing metadata rather than automatically deduplicated. No external merchant mandate, confirmed cancellation, future charge, or calibrated fraud risk is established by this synthetic data.

## Original July–September 2026 sample

- 6,681 validated bill candidates; 6,561 `monthly`, 120 `monthly_candidate`.
- All 6,561 `monthly` candidates have recent consecutive-month support in this sample.
- 19,938 distinct supporting transaction IDs (across reported bill candidates).
- 267 bills with multiple payments in a month; all 267 have a same-day, same-amount group. There are seven cases with an individual-payment-versus-monthly-median gap greater than 10%.

These are reproducible sample observations, not universal expected counts for October or other banks.

## Reproduce and inspect

```bash
python -m pipeline data/
python -m pytest -q tests/
python - <<'PY'
import json
from pathlib import Path
summary=json.loads(Path('outputs/bill_validation_summary.json').read_text())
print(json.dumps(summary, indent=2))
PY
```

On re-delivery of identical bank source files, the ingestion manifest is reused; reclassification and revalidation still run against active Silver. The four employer-scored CSV schemas remain unchanged. The October simulation tests the new reporting-month cutoff independently of the real October feed, which is not included.
