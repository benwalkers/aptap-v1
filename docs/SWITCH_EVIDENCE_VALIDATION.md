# Provider-switch evidence validation (Release 2, business-quality gate)

## Purpose and boundary

`switches.csv` is an ApTap employer-scored **candidate** table. Its five column names and order are untouched:
`customer_id,category,old_merchant,new_merchant,first_month_with_new`.
The supplemental `outputs/switch_evidence.csv` provides transaction-level evidence, and
`outputs/switch_validation_summary.json` records the independent Silver verification.
The commercial HTML report uses that verification summary. No customer switches or savings
are presented as externally confirmed.

## Algorithm

1. Read *trusted* merchant aliases only; provisional ten-class predictions with `needs_review=true`,
   `not_a_bill`, credits and unsupported providers cannot become business evidence.
2. For each customer and category, find an old and a new provider with non-overlapping
   payment **months**. The old provider's last month must precede the new provider's first
   by at most two months. Require the new provider in the reporting month, exactly two
   trusted providers, and precisely one candidate old→new direction.
3. Record every involved active canonical `transaction_id` and booking date separately
   for the old and new providers. Medians are computed from **observed positive debit magnitudes**;
   `old_amount - new_amount` is an observed payment difference, *not verified savings*.
4. Evidence levels use **distinct observed months**, never a raw transaction count:
   - `PROVISIONAL`: only one distinct month on the new-provider side.
   - `REPEATED_NEW_PROVIDER`: at least two new-provider months, but fewer than two old-provider months.
   - `SUPPORTED_PAYMENT_PATTERN`: at least two distinct months on *both* provider sides.
     This is stronger **payment-pattern evidence**, not external contract confirmation.
5. The standalone validation in `pipeline/switch_validation.py` independently reads active
   Silver and checks IDs, customer, mapped provider/category, trust status, amount sign,
   dates, non-overlap, gap, report-month recency, counts, months, medians and differences.
   It also checks that **all** eligible Silver payments for both providers were included
   and there is no undisclosed third provider. Any inconsistency raises
   `SWITCH_EVIDENCE_INVALID` and stops publication of Gold CSV outputs.

The validator uses batched SQL lookups. The source model lacks an authoritative contract ID,
provider cancellation notice, tariff details, consumption or meter readings, so **no** evidence
level proves a contract switch. Neither positive `saving` nor a bootstrap confidence interval
is evidence of causal savings. Provider/product identity is based on demo aliases, not
independently bank-approved merchant identities.

## How to run

```bash
bash scripts/workflows/00_setup_venv.sh
bash run_all.sh
```

Run the pipeline alone to regenerate and validate the current outputs:

```bash
.venv/bin/python -m pipeline data/
```

On a clean July–September sample, expected observations are **209 candidates**: 87 provisional,
122 with repeated new-provider months, 0 supported two-sided patterns, and 0 externally
confirmed. The validator references 633 distinct active Silver transaction IDs, not 209
independently verified contracts. The observed old-minus-new payment difference is positive
in 162 candidates and negative in 47. These are descriptive candidate counts only.

When the actual October file arrives, the default reporting cutoff advances to 2026-10-31.
The same checks execute and the evidence counts can change.

## Outputs

- `outputs/switches.csv`: unchanged employer-scored schema; all candidate switches retained.
- `outputs/switch_comparisons.csv`: unchanged existing comparison columns; evidence is a candidate flag.
- `outputs/switch_evidence.csv`: auditable source IDs, dates, distinct-month counts,
  payment counts, chronology/gap, evidence level and explicit unverified statuses.
- `outputs/switch_validation_summary.json`: verification result, tier counts,
  positive/negative observed differences and disclaimers.
- `outputs/run_metrics.json` and `report/one_page_report.html`: summary and qualifying wording.

Do not export full transaction-level evidence to third parties in a real bank without an
approved access policy. Restrict and tokenise identifiers as appropriate inside the bank.
