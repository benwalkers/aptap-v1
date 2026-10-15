# ApTap reporting enhancement — commercial and classification governance

This is a **reporting-only** change. It does not edit source files, `work/incremental.sqlite`, the curated alias registry, the four employer-required CSVs, or the accepted classification policy. `pipeline/report.py` is enhanced to publish the commercial report whenever the normal pipeline runs. `scripts/workflows/15_build_reports.sh` generates a fully self-contained offline Plotly dashboard from already calculated data.

## Usage

From the existing project root, **after installing the patch**:

```bash
bash run_all.sh
open report/one_page_report.html
open report/risk_dashboard.html
```

The workflow runs step **15** automatically after the merchant governance audit and scenario calculations. To rebuild the dashboard alone without rerunning ingestion, ML tests or the pipeline:

```bash
bash scripts/workflows/15_build_reports.sh
```

MiniLM is optional. If `models/minilm/modules.json` is already present and `sentence-transformers` is installed, enable diagnostic semantic predictions:

```bash
bash scripts/workflows/14_evaluate_pr_curves.sh --with-minilm
bash scripts/workflows/15_build_reports.sh --with-minilm
```

Or `DASHBOARD_MINILM=1 bash run_all.sh`. The optional semantic path operates on unique merchant descriptions (review cases and accepted high-risk cases) and never promotes/approves predictions. It is deliberately **not** required for the normal project setup. You do not need to reinstall or retrain MiniLM.

## Files

| File | Description |
| --- | --- |
| `report/one_page_report.html` | Mandatory portable print-ready commercial report with true share-lower SVG chart, amounts and bootstrap ranges. |
| `report/risk_dashboard.html` | One-file offline interactive Plotly dashboard (Plotly.js bundled within file). |
| `outputs/dashboard/monthly_classification_risk.csv` | Risk breakdown and acceptance metrics for each month, separately by source delivery vs booking month. |
| `outputs/dashboard/model_comparison.csv` | Actual TF-IDF candidate and optional MiniLM diagnostic candidate, separate similarity scores, agreement, current acceptance and risk. |
| `outputs/dashboard/review_priority.csv` | Unique descriptions needing human review and accepted high-risk descriptors; deduplicated priority candidates. |
| `outputs/dashboard/commercial_candidate_months.csv` | Candidate new-provider start month vs payment difference and lower-payment percentage. |
| `outputs/dashboard/policy_sensitivity.json` | Existing read-only conservative alias scenario; no promoted classifications. |

## Dashboard views

1. **Data quality funnel**: source-period raw/rejected/active record reconciliation; classification totals depend on selected **source delivery** or **booking month**. August contains late July-dated transactions, hence the cohorts differ.
2. **ML inference**: TF-IDF and (optionally) MiniLM are independent diagnostic suggestions. MiniLM has zero weight in final category selection; no calibration or automatic acceptance is implied. The benchmark uses the 57 corrected provided descriptions as a limited leave-one-description-out ranking experiment, not a production test set.
3. **Governance risk and review**: qualitative tiers (`high`, `medium`, `low_to_medium`, `unassessed`) from the audit; merchant-level drill-down, debits and distinct customer counts. Existing `CURATED_DEMO` mappings are **not** bank-verified ground truth. A high-risk accepted alias is flagged as a conflict between the two control systems, not silently revoked. Debit volume means transaction exposure, not customer losses.
4. **Commercial sensitivity**: switch comparisons grouped by **first month with new provider**. The baseline vs conservative policy comparison covers the **entire reporting period through `as_of`**, not the selected month, and is labelled accordingly. Counts of candidate bills removed are not validated false positives or verified savings.

No personal customer or transaction identifiers are embedded in the browser report. Merchant descriptions are included for review (synthetic input; still treat as potentially sensitive). The dashboard reads SQLite **read-only** and publishes aggregates; external CDN calls, browsers servers and additional Python dependencies are unnecessary.

## Verification

```bash
bash scripts/workflows/02_run_tests.sh
bash scripts/workflows/06_verify_rerun.sh
```

The existing four employer-required CSVs and their schemas must remain byte-identical for unchanged inputs. If optional MiniLM diagnostics are desired, rebuild the dashboard explicitly using the `--with-minilm` command; running the default `run_all.sh` resets the view to lexical-only diagnostics.

**Plotly.js attribution:** the bundled `dashboard/vendor/plotly.min.js` is Plotly.js v3.3.1, released by Plotly, Inc. under the MIT licence. See `dashboard/vendor/PLOTLY_LICENSE.txt`.
