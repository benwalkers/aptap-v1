# ApTap Merchant Governance Audit — Release 2

**Scope:** All 92 canonical merchant descriptions in the supplied July–September synthetic transactions; 133,692 clean transaction occurrences. This is an inference/governance audit, **not** an independent source-of-truth verification or model retraining exercise.

## Core findings

| Measure | Existing Release 2 | Conservative hypothetical policy |
|---|---:|---:|
| Unique descriptors | 92 | 92 |
| Accepted under demo mapping | 71 | 69 |
| Review-required (internal status) | 21 | 23 |
| Transactions flagged for review | 15,033 | 15,884 |
| Recurring-bill candidates | 6,681 | 6,401 |
| Provider-switch candidates | 209 | 209 |

The two additionally flagged accepted aliases are `ADMIRAL INS DD` (389 transactions) and `ADMIRAL INSURANCE` (462 transactions). Their descriptions identify an insurer but not necessarily *car* insurance. Removing their demo mappings removes **280** recurring-bill candidates in the scenario. Nothing is changed in the active registry until someone explicitly approves the policy.

Two erroneous human labels were **already corrected in Release 2** while preserving the original CSV: `OCTOPUS ENERGY` from `broadband` to `energy`; `TESCO MOBILE` from unsupported `groceries` to `mobile`. There are **no new automatic approvals** in this audit.

## What should be reviewed, at the group level?

| Reason | Descriptors | Transaction occurrences | Resolution path |
|---|---:|---:|---|
| Generic counterparty/payee | 1 | 8,605 | Counterparty or MCC; cannot infer `water` |
| Insurance product not identified | 9* | 3,559 | Insurer identity alone cannot establish home vs car |
| Multi-product telecom provider | 9 | 2,002 | Product code/verified payment reference |
| Council payment without tax evidence | 1 | 807 | Council-tax reference/service code |
| Bundled Prime membership | 2 | 640 | Business taxonomy policy for Prime membership |
| British Gas Services | 1 | 271 | Determine energy supply vs service/cover |

*Includes the two formerly accepted Admiral aliases; the original 21 flagged descriptors comprise seven insurance descriptions plus the other groups.*

## Evidence policy

- **Never promote a description solely because lexical/MiniLM similarity is high or both methods agree.** Scores are not calibrated correctness probabilities.
- `not_a_bill` is a positive business decision; `REVIEW_REQUIRED` is an internal abstention status (not a scored category). Treat them differently.
- Synthetic `CURATED_DEMO` mappings demonstrate the pipeline, **not bank approval**. An accepted merchant category is not proof of a recurring payment or confirmed provider switch.
- Preserve original labels in `data/merchant_labels.csv` and active demo mapping in `classification/curated_aliases.csv` for reproducibility. The proposed alternative stays in `outputs/merchant_governance/proposed_aliases_conservative.csv`.
- Triage **unique canonical descriptors**, not thousands of individual transactions; prioritize by affected volume, potential impact and uncertainty. Sample accepted predictions as well as flagged cases to detect false confidence.
- Human reviewers should not invent absent product information. Request permitted customer/account/product metadata, and retain `needs_review=true` when insufficient.

## Outputs

- `outputs/merchant_governance/merchant_audit_all_92.csv`: full inventory, current and proposed classification, volume, existing human label, rationale and evidence needed.
- `outputs/merchant_governance/merchant_review_proposals.csv`: 23 actionable exceptions, ranked with the two potential demotions first, then volume.
- `outputs/merchant_governance/merchant_label_corrections.csv`: the two established correction records.
- `outputs/merchant_governance/proposed_aliases_conservative.csv`: hypothetical alias reference **without** the two Admiral mappings.
- `outputs/merchant_governance/merchant_governance_summary.json`: coverage/review counts.
- `outputs/merchant_governance/scenario_impact.json`: downstream feature comparison (baseline and proposed conservative catalogue).
- `outputs/merchant_governance/scenario_removed_bills.csv`: 280 removed bill-candidate keys in the scenario.
- `outputs/merchant_governance/scenario_removed_switches.csv`: removed switch candidates (none for this scenario).

## How to reproduce in your existing local project

```bash
source .venv/bin/activate
python scripts/audit_merchant_registry.py
python scripts/compare_merchant_scenarios.py
```

Or use the added shell scripts:

```bash
bash scripts/workflows/12_audit_merchants.sh
bash scripts/workflows/13_compare_review_scenario.sh
```

These jobs are **read-only with respect to ingestion state, original files and the active curated alias catalogue**. They write only into `outputs/merchant_governance/` and use `outputs/clean_transactions.csv` already produced by your incremental pipeline.

## Next release gate

Request bank/product reference evidence for ambiguous labels; record reviewer, time, evidence and catalogue version before accepting. Promote a new catalogue only after a regression test confirms that bill/switch metrics change as expected. The current proposal is an audit artifact and does not represent a model accuracy improvement or independently verified labels.
