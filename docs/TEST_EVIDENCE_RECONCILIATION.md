# Test evidence reconciliation — 15 October 2026

**Current result: 54 collected, 54 passed, zero failures/skips**, executed only in a
disposable project copy. See [collection inventory](release_evidence/phase2/test_inventory.json),
[collection log](release_evidence/phase2/test-collection.txt) and
[full workflow log](release_evidence/phase2/workflow.txt). Pytest reports **0.59 s**
for the test stage; collection is a separate command, not an additional test run.

## Historical claims and their limits

| Claim | Historical evidence available | Interpretation |
|---|---|---|
| 38/38 passed | Root `RELEASE_VALIDATION.md`, dated 2026-10-14, explicitly reports 38/38 and switch-validation negative tests | Historical narrative evidence; original raw test-session log and Git revision are absent |
| 54/54 passed | Supporting revised Notes, its two-page preview and knowledge base §3.4/§11 report the later 54-test suite; reporting/bill docs describe their added coverage | Historical narrative evidence, not original test logs; now independently matched by this audit's current execution |
| 66 cached IDs | Pre-existing `.pytest_cache/v/cache/nodeids` has 66 entries and empty `lastfailed` | Stale cache includes 12 IDs from absent `tests/test_release1.py`; not collection or proof of 66 passing current tests |

The present inventory explains the **16-test difference** exactly: 12 bill-evidence
cases plus 4 reporting cases. Excluding those two files leaves 38 current cases.
That is a source-supported explanation consistent with the dated release/reporting
notes, **not proof of the historical command, commit or precise addition order**.
Git metadata is absent and raw historical logs cannot be reconstructed.

## Current collected inventory

| Test module | Collected cases | Scope |
|---|---:|---|
| `test_pipeline_core.py` | 12 | Schema/date/identity, reconciliation, reruns, corrections, malformed inputs, review boundaries |
| `test_employer_contract.py` | 5 | GBP variations, correction audit, invalid replacements, ten categories, October cutoff |
| `test_switch_evidence.py` | 14 | Transaction lineage, month evidence, overlap/untrusted providers, omitted payments, tampering |
| `test_merchant_governance_audit.py` | 4 | Sample inventory, no promotions, conservative registry/scenario outputs |
| `test_evaluation_packaging.py` | 3 | Dependency profiles, evaluation files and setup script references |
| **Earlier-scope subtotal** | **38** | Current files consistent with the earlier documented count |
| `test_bill_evidence.py` | 12 | Complete current-month bill set, medians, recurrence, forecasts, duplicate-like payments, tampering |
| `test_reporting_dashboard.py` | 4 | Source/booking cohorts, reconciliation failure, safe embedded JSON, commercial report edge cases |
| **Current total** | **54** | Seven files |

There are **42 test functions**. Parameter expansion adds five bill-tampering cases
(six values for one function) and seven switch-tampering cases (eight values for one
function), yielding 54 collected cases. Counts refer to collected cases, not functions.

## Commands, environment and state safety

From the disposable copy, using an independent copy of the existing `.venv/`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .venv/bin/python -m pytest --collect-only -q tests/
bash run_all.sh
```

The workflow executes `bash scripts/workflows/02_run_tests.sh`, whose actual command
is `.venv/bin/python -m pytest -q tests/`. Environment: Python 3.14.3, pytest 9.1.1,
macOS 26.5.1 arm64. `PYTHONPATH` was removed and Python resolved packages from the
copied environment; no package installation was needed. Original `work/`, outputs,
reports, caches and `.git` were excluded from the copy. Tests with temporary fixtures
used their own temp directories; governance tests ran after workflow steps 12/13
produced the required isolated outputs. This ordering matters on a clean run.

`run_all.sh` delegates to `scripts/workflows/run_all.sh`; the actual order is
**01 → 03 → 04 → 05 → 12 → 13 → 14 → 15 → 02 → 06**. The earlier run guide's claim
that tests ran before ingestion was inaccurate and has been corrected. No tests or
implementation were edited to obtain this result.

## Boundaries and next action

- Historical timings of 7.678 s/82.8 MiB and 8.5 s/41.3 MiB cannot be reconciled to
  exact historical hardware/commands from available logs. They remain historical
  reports; current fresh/run and rerun measurements are separated in
  [release readiness](RELEASE_READINESS_AUDIT.md).
- No hidden employer October input, production/bank deployment, Docker runtime,
  Spark/Iceberg parity, independent model precision or full air-gap enforcement was
  tested. These are outside the demonstrated local suite.
- Retain historical claims with dates and limitations; use **54 collected/54 passed
  in this isolated audit** as the current result. Supply genuine historical session
  exports if provenance of earlier claims must be established.
