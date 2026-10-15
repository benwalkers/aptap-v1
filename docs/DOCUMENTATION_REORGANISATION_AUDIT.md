# Documentation reorganisation audit — 15 October 2026

## Scope and pre-change state

Execution directory: existing `aptap-v1/` project. The complete supplied task guide
was read before edits. No `.git` directory/file exists here or in its ancestors:
`git rev-parse --show-toplevel`, `git status --short`, `git branch --show-current`
and `git ls-files` each failed with “not a git repository”. Branch, tracked/untracked
status and prior user edits therefore cannot be established. Git was not initialised.
No AGENTS.md guidance was found in the project or applicable parent directories.

A SHA-256 manifest of all 148 pre-existing files outside `.venv/`, and copies of all
project Markdown outside `.venv/` and `.pytest_cache/`, were saved in an external
local audit directory (location reported to the reviewer). No pre-existing content
was discarded; original README/index versions remain in that backup.

## Candidate inventory and decisions

Git tracking status is **unknown for every item** because Git metadata is absent.
An `rg` search of Markdown/HTML and runtime/scripts/tests found no code dependency
on the three moved paths. There were no destination copies, older dialogue variants,
or authentic exports to compare. No merge or deletion was performed.

| Candidate | Purpose / reference use | Decision |
|---|---|---|
| Root README | Reviewer commands and narrative; code/docs remain at their paths | Edited for navigation, contracts and evidence status; original backed up |
| Root NOTES | Canonical Part D; assignment requirement | Held byte-for-byte; comparison below |
| Original assignment | Exact employer brief | Held byte-for-byte |
| Release validation / run guide | Recorded execution evidence / detailed workflow | Held byte-for-byte; root README points to both |
| Root merchant governance audit | Audit reference used by documentation | Held in root byte-for-byte |
| Existing five docs (architecture, deployment, bill, switch, reporting) | Technical/design/validation references | Held byte-for-byte, indexed |
| Knowledge base in ai_transcripts | Curated supplementary reference; self-identifies as non-transcript | Moved to docs/knowledge_base byte-for-byte; historical source names retained |
| Enhanced dialogue PDF | Cover explicitly says synthetic editorial reconstruction | Moved to supplementary byte-for-byte |
| Part D PDF preview | Supporting revision preview, not canonical root Notes | Moved to docs/submission byte-for-byte |
| Revised Part D Markdown | Distinct supporting version, not identical to root | Retained at original path byte-for-byte and explicitly catalogued as supplemental; promotion held |
| Existing AI index | Required missing-history instructions; no share URLs/session IDs | Replaced with transparent provenance table; original backed up |

## Completed moves

All moves used non-overwriting `Path.rename` after checking destination absence,
the filesystem equivalent of `mv`. `git mv` was unavailable. Nothing is staged.

| Old path | New path | SHA-256 (same before/after) |
|---|---|---|
| `ai_transcripts/ApTap_Engineering_Knowledge_Base_Complete.md` | `docs/knowledge_base/ApTap_Engineering_Knowledge_Base_Complete.md` | `19732d2006adb5fcc51ae8226d1015b7e95347a75eaddf472c9fb4417e7686c0` |
| `ai_transcripts/ApTap_Reconstructed_AI_Engineering_Dialogue_Enhanced.pdf` | `ai_transcripts/supplementary/ApTap_Reconstructed_AI_Engineering_Dialogue_Enhanced.pdf` | `3a3e4cf6be100812adea4d3784503cac99a03b554ea3ad211eaf446d4051c22c` |
| `ai_transcripts/NOTES_ApTap_PartD_2Page_Preview.pdf` | `docs/submission/NOTES_ApTap_PartD_2Page_Preview.pdf` | `a80daa7245bf00d5f1d6a7d8fa8eee4a500eab8b50773ad5aab722983458afef` |

## Canonical Part D comparison gate

Version precedence is not established by filesystem dates or “Revised” in a filename.
The supporting version adds useful material but is not an evidence-equivalent
replacement. Both remain available; no silent promotion or content merge occurred.

| Required topic | Root NOTES.md | Supporting revision | Decision / gap |
|---|---|---|---|
| Assignment points / raw-data problems | Covers migration, back-posting, invalid identities, corrections | Adds measured EDA table, repeated-ID and descriptor counts | Both cover brief; extra figures remain reported evidence |
| Untrusted outputs / model limits | Explicit synthetic demo aliases, minority-label scarcity, unconfirmed candidates | Adds numeric exploratory scores, coverage and Admiral risk flags | Retain root's explicit demo-governance caveat; accepted is not independently approved |
| AWS and fully bank-contained | Both proposed settings, no egress and approved software | More detailed orchestration, manifests and bank change controls | No cloud deployment or bank approval verified |
| 15m scale / runtime and memory | 449.5m monthly rows, ~64.6GB; consult metrics, rejects naive capacity extrapolation | Same density plus ~7.1h scenario and 7.678s/82.8MiB fresh-run claim | Claims differ across references; no fresh-run log supplied to establish precedence |
| Storage / privacy / retention | Partitioning, correction audit, minimisation, encryption, retention | Expanded clustering, sensitive fields and contract-specific retention | Substantive distinct wording retained |
| Cost per million | Measurement method; avoids unverified laptop-to-cloud price | Assumed Glue compute-only $0.063/million, explicitly illustrative | Neither is measured all-in production cost |
| ML monitoring | Review/precision, backlog, drift and category-mix monitoring | Proposed macro-F1 decline and PSI thresholds, challenger governance | Revision's gates are proposals, not active controls |
| First week | Contract, sequence metadata, merchant review, synthetic load tests | Expanded security, reviewed sample, baseline/SLA plan | Both retained |
| AI provenance | Complete exports/share links required | Complete exports, IDE history and reconstructed-history distinction | Originals remain missing |
| Implementation boundaries | Says additive JSON keys are ignored safely | Says fail/quarantine unsupported schema rather than silently discard fields; describes approved/reviewed aliases | Wording/approval ambiguity requires reviewer decision; no code changes authorised |
| Rendered length | Two-page target only | Preview PDF has two pages | Root Markdown page count NOT RE-VERIFIED |

Root and revised Markdown hashes:
- `NOTES.md`: `1ce6f7dbeee38049e4837a0b03d913739e528f722ed68aa2225658cc723eb9a4`
- `ai_transcripts/NOTES_ApTap_PartD_Revised.md`: `75a06ec1c7c8d90f9960e90c72f42a7272dcd4a72014f63965ed2b8c134f4a5e`

No suitable local Markdown renderer was found (`pandoc`, `wkhtmltopdf`, `typst`
not available; Python `markdown`/`weasyprint` not installed). No dependencies were
installed. `pypdf` confirmed 2 preview pages and 15 reconstruction pages, not root
Markdown pagination. Visual/root page-limit approval remains required.

## Preserved reference conflicts and evidence gaps

- `RELEASE_VALIDATION.md` records 38/38 tests; revised Notes and knowledge base
  report 54/54. These may represent different revisions; no raw test-session log
  establishes which suite ran against this checkout. Neither count was rerun here.
- Deployment notes report about 8.5 seconds / 41.3 MiB for a fresh run; revised
  Notes and knowledge base report 7.678 seconds / 82.8 MiB. Existing run metrics
  instead record 3.073 seconds / 70.7 MiB and zero new batches. Different runs must
  not be conflated; source fresh-run logs are needed for reconciliation.
- Knowledge base section 4.4 says exact CLI flags, including `--as-of`, were not
  independently established. Current source explicitly implements `--as-of` and
  automatic source-period cutoff; README now documents those source-verified facts.
  Historical reference wording was preserved rather than silently rewritten.
- Run guide describes a ZIP without state and uses `aptap-release2`; this local
  working folder is `aptap-v1` and contains runtime state/models. ZIP-era packaging
  statements do not establish this folder's release contents. README now uses the
  actual project root and avoids claiming state/model weights are absent.
- Long-form knowledge base cites earlier knowledge-base and reconstructed Markdown
  source filenames that are not in this checkout. Those historical inventory names
  are not fabricated as new files; the available PDF is indexed explicitly.
- No authentic full AI exports, verified chat share URLs, or complete coding-agent
  histories were found. This session also needs a native export. No originals were
  relocated or edited. Completeness is a submission blocker.
- Docker, AWS/bank deployment, Spark/Iceberg CDC parity, production accuracy,
  externally confirmed switches/savings, PSI automation and retraining remain
  unverified or proposed. Existing documents largely label these boundaries;
  no implementation/deployment completion is inferred from design prose.

## Edits and reference repair

Edited root README and AI provenance README; added docs navigation, submission
supplement index and this audit. Direct relative links now discover all moved
artefacts. No inbound Markdown link to an old moved path required repair. Historical
bare source filenames in the untouched knowledge base are retained as provenance.
No original assignment, Notes, run guide, validation report or engineering reference
was rewritten. No source, execution script, configuration or Docker file changed.

## Validation outcome

See final audit verification below. Runtime tests and the pipeline were deliberately
not executed because they can modify outputs/state; no fresh execution claim is made.
No network, dependency installation, commit, push, Git initialisation, remote change,
export of bank/client data, merge, deletion or staging was performed.

### Final audit verification

- SHA-256 comparison of all 148 original files outside `.venv/`: only root README
  and the AI README have changed contents. All three moves match original hashes;
  all remaining original paths exist with identical hashes, including source data,
  Python/scripts/tests/configs, model files, CSVs, report HTML and all `work/` files.
  `.venv/` was excluded from hashing and no environment modification was performed.
- All 11 required/root submission artefacts checked present. CSV headers were read
  directly: clean 133,692; rejected 1,463; bills 6,681; switches 209, matching the
  contracts now printed in README. This is file inspection, not a pipeline rerun.
- Dependency-free Python Markdown-link heuristic checked 50 local links with
  **zero missing targets**. External URLs were not accessed or verified; fragment
  anchors were not independently checked. `rg` old-path hits are audit history,
  intentionally retained supplemental Notes, or historical source inventory names.
- `git diff --check` and `git diff --cached --check` could not run in repository
  mode because metadata is absent. `git diff --no-index --check` against external
  backups (or `/dev/null` for new docs) emitted **zero whitespace/conflict-marker
  diagnostics** for all five authored Markdown files. Exit 1 indicates content
  differences in no-index mode, not whitespace failure.
- New/edited docs plus the moved supplements and held revision were scanned for
  common credential tokens, private keys, assigned secrets, absolute home paths
  and email-account patterns: **zero matches**. Manual context review found no
  unrelated project names/account IDs in the new summaries. This pattern audit
  is not a guarantee of secret absence; authentic exports remain missing.
- New documentation: `docs/README.md`, `docs/submission/README.md`, and this audit.
  Changed existing documentation: root README and AI README. Nothing staged,
  committed or pushed. A unified review patch and original Markdown backups are
  available in the external local audit directory reported to the reviewer.

Status: **DOCS_REORGANISATION_PARTIAL**. Safe arrangement/navigation is complete;
Git-history availability, authentic AI evidence, root Notes pagination and evidence
reconciliation remain unresolved. Review the patch/Notes comparison, supply genuine
session exports, and separately plan any isolated execution before submission.
