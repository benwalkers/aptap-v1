# Release 2 — Current local release validation (2026-10-15)

**Verified in an isolated fresh-state copy:** `bash run_all.sh` exited 0;
**54 collected tests / 54 passed in 0.59s**. Fresh pipeline: **8.842s / 64.4MiB**,
three batches committed; same-input rerun: **3.146s / 73.0MiB**, zero new batches,
four mandatory CSVs byte-identical and equal to the original checkout's outputs.
Reconciliation: **135,155 = 133,692 + 1,463**; 6,681 bill candidates and 209 switch
candidates; automatic and independent read-only evidence checks passed.
Synthetic October also passed; the actual employer October file is absent.
Original data, outputs, reports, models and SQLite state were not modified.

Full [release-readiness audit](docs/RELEASE_READINESS_AUDIT.md),
[test evidence reconciliation](docs/TEST_EVIDENCE_RECONCILIATION.md), and
[execution log](docs/release_evidence/phase2/workflow.txt).
Historical measurements below were not silently promoted into current results.
Original full AI exports/share links/coding-agent histories remain required.

---

# Release 2 — Switch evidence validated (2026-10-14)

The included outputs were generated from the original three July–September 2026 source files.
No actual October employer file, external contract cancellation evidence or bank-approved
merchant labels were provided. The PySpark/Iceberg and AWS profiles remain reference-only.

## Historical reported build evidence — not the current audit

- Local raw reconciliation: **135,155 occurrences = 133,692 active + 1,463 rejected/superseded**.
- **6,681** recurring-bill candidates and **209** provider-switch candidates.
- **38/38 tests passed**, including negative tests for missing transaction evidence,
  incomplete provider history, tampered amounts/dates, false confirmation claims,
  multiple payment occurrences in a single month, and concurrent providers.
- All **four employer-required output CSVs remain byte-identical** to the preceding
  Release 2 baseline; prescribed headers are unchanged.
- `outputs/switch_evidence.csv` contains 209 rows with references to **633 distinct
  canonical transaction IDs**. Independent Silver validation returns `PASSED`.
- Candidate evidence: **87 provisional**, **122 repeated new-provider months**,
  **0 supported two-sided payment patterns**, **0 externally confirmed switches**, and
  **0 verified savings**. Payment differences are lower for 162 candidates and higher
  for 47; neither direction is a verified causal saving.
- Identical file rerun: **0 new committed batches**, with the four required CSVs
  byte-identical across reruns.
- Exploratory lexical benchmark: accuracy 0.789, macro-F1 0.635,
  macro-AP 0.698 on 57 leave-one-description-out labels. No independent holdout.
- Isolated synthetic October run passed: **135,158 raw = 133,693 active + 1,465 rejected**,
  as-of October 31; **one** provisional switch candidate was traced and validated.

## Boundaries

The complete numbered workflow was tested against preinstalled testing/evaluation
libraries. This sandbox **did not independently perform a fresh online pip install**.
The default `python -m pipeline data/` code path uses Python's standard library.
Optional MiniLM download and offline execution were successfully demonstrated on the
user's Mac previously, but MiniLM weights are not part of the ZIP. No Docker build,
production Spark execution, bank deployment, or actual October data was verified.

**Important:** the provider mapping depends on demo-accepted aliases, which do not
prove bank-verified product identity. See `docs/SWITCH_EVIDENCE_VALIDATION.md`.

Full AI conversation transcripts and sharing links must be supplied by the candidate
before the final employer submission; they are not fabricated or included here.

## Additional recurring-bill evidence gate (2026-10-15)

The independent `pipeline/bill_validation.py` validates all 6,681 sample bill candidates against 19,938 active trusted debit IDs. 6,561 have recent consecutive-month evidence and 120 remain provisional. 267 candidate bills have same-day repeated-payment groups, and seven have an individual-payment versus monthly-total median difference over 10%. These are diagnostics, not bank-confirmed duplicate transactions or verified recurring contracts. Four employer-scored CSV schemas remain unchanged; see `docs/BILL_EVIDENCE_VALIDATION.md`.
