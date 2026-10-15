# Release readiness audit — 15 October 2026

**Status: RELEASE_READY_PENDING_AI_EXPORTS.** The documented native workflow and all
54 collected tests passed in an isolated fresh-state copy. Required CSVs reconcile,
retain exact schemas and match both rerun hashes and original checkout bytes.
Canonical root Notes is now consolidated and verified as two rendered A4 pages.
Authentic complete AI exports, applicable verified chat share links and coding-agent
histories remain the precise outstanding submission blocker.

This status covers the native take-home release, not production approval, the unseen
employer October file or optional cloud/container/model execution paths. No Git
initialisation, staging, commit, push, Python implementation change, Docker addition,
cloud deployment or repeat of Phase 1 document moves occurred.

## Evidence and environment

| Item | Observed value |
|---|---|
| Execution date / client timezone | 2026-10-15 / Europe/London |
| Host | macOS 26.5.1 arm64 |
| Python | 3.14.3, Clang 16.0.0 |
| SQLite | 3.50.4 |
| Packages | pytest 9.1.1; NumPy 2.5.4; scikit-learn 1.9.1; Matplotlib 3.11.2 |
| Environment provenance | Independent copy of existing installed `.venv/`; no dependency installation |
| Fresh pipeline | 8.842 s, 64.4 MiB peak RSS; 3 committed batches |
| Same-input rerun | 3.146 s, 73.0 MiB peak RSS; 0 new batches |
| Entire `bash run_all.sh` | Exit 0, 59.652 s wall time including first Matplotlib font cache and tests |
| Tests | 54 collected, 54 passed in 0.59 s; no failures/skips |

Fresh and replay metrics are different workloads and different processes; peak RSS
is the pipeline's `resource.getrusage` measurement, not whole-workflow RSS.
Old 7.678s/82.8MiB and 8.5s/41.3MiB figures remain historical reports, not current
results. This checkout's original run metrics are unchanged (3.073s/70.7MiB rerun).
Current independent environment details are in [independent checks](release_evidence/phase2/independent_checks.json).

## Isolation and commands actually executed

An external temporary project copy excluded `.git/`, `.venv/`, `work/`, `outputs/`,
`report/`, bytecode, pytest cache and `.DS_Store`; an independent environment copy
was then placed at its `.venv/`. Empty output/report directories were created, with
no SQLite/Bronze state. Inputs, code and optional model files were copied rather
than linked to the original. The environment's interpreter points to the installed
system Python; its project environment/package directory is the copy. No source
project directory or state symlink exists.

From that disposable project's root:

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
# MPLCONFIGDIR points to an external temporary cache; PYTHONPATH was removed.
.venv/bin/python -m pytest --collect-only -q tests/
bash run_all.sh
bash scripts/workflows/07_optional_october_demo.sh
```

The full workflow followed **01, 03, 04, 05, 12, 13, 14, 15, 02, 06** without any
implementation/script edit. Step 06 reran the pipeline and compared all four CSVs.
An external read-only Python audit helper independently read headers/rows/hashes,
opened the copy's SQLite using URI `mode=ro` plus `PRAGMA query_only=ON`, ran
`PRAGMA integrity_check`, and called existing `validate_bills`/`validate_switches`
against generated CSVs and active Silver. It passed; an initial helper import-path
issue was fixed only in the external helper, not the application.

Raw logs, helper and disposable environment remain in an external local audit
directory reported to the reviewer. Repository copies of logs replace only the
machine-specific temporary project prefix with `<ISOLATED_PROJECT>`:
[workflow](release_evidence/phase2/workflow.txt),
[collection](release_evidence/phase2/test-collection.txt),
[synthetic October](release_evidence/phase2/october-demo.txt).
No log was reconstructed as an AI conversation.

## Required contracts, hashes and reconciliation

Both fresh and rerun counts are **135,155 raw = 133,692 active + 1,463 rejected**.
The rejected ledger has 1,423 canonical duplicate occurrences and 40 missing customer
IDs. Sample corrections/supersessions/conflicts are zero; correction semantics are
covered by tests with dedicated fixtures. Original input file digests match copied
inputs and the fresh run's manifest. Source and output schemas were read directly.

| Required CSV | Rows | Exact header |
|---|---:|---|
| `clean_transactions.csv` | 133,692 | `transaction_id,customer_id,booking_date,amount,description` |
| `rejected_rows.csv` | 1,463 | `source_file,source_line,transaction_id,reason,raw_json` |
| `recurring_bills.csv` | 6,681 | `customer_id,merchant,category,cadence,typical_amount,next_expected_date` |
| `switches.csv` | 209 | `customer_id,category,old_merchant,new_merchant,first_month_with_new` |

All four mandatory files are byte-identical between fresh and replay execution,
and independently match the original checkout's files, which were never overwritten.

| File | SHA-256 |
|---|---|
| `clean_transactions.csv` | `51c414b49cf55d909da11e91071e0f561b4ea3b6ae342b5a11591f25c31d5801` |
| `rejected_rows.csv` | `e96798d578d45169b4c2356fbc0d6957a8b804b0323918851a63c2de1e402784` |
| `recurring_bills.csv` | `5cbc83518d921dbf727b52cb2a7bcbbb8fad8607d1018a3b09ac416ddbbe2050` |
| `switches.csv` | `25134c08a832f0f37d831fb2d83ee461ab0e354fbe369a2e3b7ab89cf79498cb` |

See [rerun hash proof](release_evidence/phase2/rerun_verification.json),
[fresh metrics](release_evidence/phase2/fresh_run_metrics.json),
[rerun metrics](release_evidence/phase2/rerun_metrics.json) and
[independent checks](release_evidence/phase2/independent_checks.json).

## Bill/switch evidence and optional October simulation

- Bills: **PASSED**, 6,681 candidates backed by 19,938 distinct trusted Silver IDs;
  6,561 recent-consecutive-month patterns and 120 provisional. 267 same-day repeated
  payment groups and seven individual-median/monthly-total gaps above 10% are
  diagnostics, not bank-confirmed duplicate transactions. Zero verified contracts.
- Switches: **PASSED**, 209 candidates backed by 633 distinct IDs; 87 provisional,
  122 repeated-new-provider patterns, zero supported-two-sided patterns, zero
  externally confirmed switches and zero verified savings. Lower observed payments
  for 162 and higher for 47 do not establish causal savings.
- `PRAGMA integrity_check` on the isolated SQLite returns **ok**. Independent
  read-only bill/switch validation also passes, beyond the automatic pipeline gate.
- Synthetic October: exit 0, **135,158 = 133,693 + 1,465**, `as_of=2026-10-31`,
  one provisional bill and one provisional switch, both evidence gates **PASSED**.
  Pipeline 8.346s / 71.5MiB; wrapper wall 8.541s. It used separate copy-local
  `work/demo_october/` data/state/output, not the actual employer October file.
  See [metrics](release_evidence/phase2/synthetic_october_metrics.json).

Raw EDA counts, differing raw fields and label imbalance are recorded in
[EDA findings](release_evidence/phase2/eda_findings.json). Raw labels include an
erroneous `groceries` entry; the scored output taxonomy remains exactly ten classes.

## Canonical Notes decision and preserved substantive content

**Chosen canonical document: root `NOTES.md`, consolidated from both versions.**
The original brief remains unchanged. Root Notes retained its explicit synthetic
alias caveat, canonical correction/reconciliation policy, security boundaries and
measurement-based cost method. The supporting revision supplied measured EDA,
minority-label/PR discussion, detailed production boundaries and proposed MLOps
gates. Both full previous versions are preserved byte-for-byte:
[previous root](submission/archived_notes/phase1/NOTES_before_phase2.md) and
[supporting revision](submission/archived_notes/phase1/NOTES_supporting_revision.md).
The existing revised Markdown and preview PDF also remain unchanged at their
Phase 1 locations. No substantive prior wording was discarded without a backup.

| Difference / conflict | Final decision and evidence |
|---|---|
| Root omitted numeric EDA/benchmarks and PSI/F1 gates | Added verified raw EDA and current lexical results; gates explicitly proposed |
| Revision called aliases approved/reviewed | Retained root's synthetic demo status; independent production approval remains absent |
| Revision could imply all unknown fields must fail | Document actual behaviour: additive JSON keys accepted, missing required fields rejected and unsupported contracts fail |
| 312 changed raw September payloads could be mistaken for corrections | Direct raw comparison confirms 312 different repeat payloads, while fresh canonical correction count is zero; wording now distinguishes formatting from true changes |
| Historical 38/54 tests | Current collection/execution is 54; historical claims preserved and reconciled in the dedicated report |
| Historical fresh/replay timings mixed | Use measured fresh 8.842s/64.4MiB and link separate rerun evidence; do not erase historical sources |
| Scale estimate in revision used ~7.1h | Recomputed from this fresh three-month throughput: 8.17h for 449.5m rows, with explicit invalid-capacity caveat; naive RSS extrapolation ~209GiB is likewise not a sizing requirement |
| Cost scenario could sound measured | Keep hypothetical $0.063/million labelled assumed compute-only; full original arithmetic remains in the archived revision |
| Historical MiniLM benchmark | Retained in unchanged reference/archive, described as historical in root Notes; optional MiniLM was not rerun |

## Two-page verification

Root Notes was rendered to [a new canonical PDF](submission/NOTES_Canonical_2Page.pdf)
through [self-contained print HTML](submission/NOTES_Canonical_Print.html), not by
reusing the old preview. The simple conversion maps Markdown headings/paragraphs,
inline bold/code and one `<!-- pagebreak -->` marker to equivalent HTML.
Markdown links become visible text labels in the print export, avoiding machine-local
file URLs; clickable project navigation remains in the Markdown.
A4, 14mm top/bottom and 16mm side margins, Arial 10pt, line-height 1.25; sections 1/2
occupy page 1 and 3/4 page 2. Its HTML embeds the source Markdown SHA-256.

Chrome's existing headless renderer ran with a disposable profile, background
networking/component updates/sync disabled and no PDF headers/footers. Reproduce
printing the supplied HTML from the project root (set `TEMP_PROFILE` to a fresh
external temp directory):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --disable-background-networking \
  --disable-component-update --disable-sync --no-first-run --no-default-browser-check \
  --user-data-dir="$TEMP_PROFILE" --no-pdf-header-footer \
  --print-to-pdf="$PWD/docs/submission/NOTES_Canonical_2Page.pdf" \
  "file://$PWD/docs/submission/NOTES_Canonical_Print.html"
```

`pypdf` confirms **exactly two pages**; `pdfplumber` rendered both to PNG and both
were visually inspected: readable text, no clipping/overlap, final content present.
Root Markdown SHA-256: `ad743b6d53c005821e743d1a5ff259cd8fc9b752a7b18e45d0a7b0ff2c27f65e`.
This proves the stated print layout, not every editor's default pagination. Regenerate
HTML/PDF after changing Notes; the old two-page preview is supplemental historical
material and is not claimed to match current root Notes.

## AI provenance and Git packaging

Reconstructed dialogue remains in `ai_transcripts/supplementary/`, explicitly
synthetic. At the Phase 2 execution audit, no original complete chat export, verified chat share URL or genuine
coding-agent history is present. Coverage of all sessions cannot be inferred from
supplementary documents; Phase 1 and this session also require native exports.
No original transcript content was generated, edited, shortened or redacted.

See [test reconciliation](TEST_EVIDENCE_RECONCILIATION.md) and
[Git packaging checklist](GIT_PACKAGING_CHECKLIST.md). Known local environment,
weights, caches and state are excluded by existing ignore rules; generic future
secret/state patterns are recommendations only. Nine credential-like scan hits in
bundled Plotly/Mapbox code were manually confirmed as empty parameters/null values
or token-handling code, not embedded credentials. A scan cannot guarantee absence.

## Findings, blockers and next actions

| Finding | Evidence | Outstanding blocker / next action |
|---|---|---|
| Native workflow/replay works | Exit-0 workflow, 54 passed, matching schemas/hashes | None for this local sample; preserve logs and review docs |
| Notes conflict and page limit resolved | Consolidated root, full archived sources, visually checked two-page render | None for stated layout; re-render any future edit |
| 38/54 discrepancy explained | Current inventory: 38 earlier-scope + 12 bills + 4 reports | Original historical run provenance unavailable; request genuine logs only if needed |
| AI deliverable incomplete | Conversation 01 share URL now supplied; no original exports/agent histories; link/content unverified | **Submission blocker:** provide pending PDF and all other full sessions; verify applicable links and completeness; review privacy |
| No Git metadata in working folder | Git root/status commands fail | Git submission step deferred as requested; locate intended history before later initialisation |
| No fresh dependency install | Existing installed environment copied | Optional follow-up clean-install/clean-clone verification; not claimed as passed |
| Actual October/production/cloud/model accuracy unknown | Only synthetic local tests/evaluation | Do not claim hidden-input pass, bank approval, deployed monitoring, parity or causal savings |

Final link/checksum/whitespace results are appended after all documentation edits.

## Final preservation and documentation validation

- Before/after SHA-256 checks account for **all 151 original files outside `.venv/`**:
  **144 unchanged** and only seven authorised Markdown files edited. No original
  file is missing; no Phase 1 move was repeated. Protected code, tests, scripts,
  source inputs, weights, four CSVs, report HTML and all original `work/`/SQLite
  files retain their original hashes. `.venv/` was copied, not reconfigured or used
  for project execution; no dependencies were installed into it.
- Edited: `NOTES.md`, `README.md`, `RELEASE_VALIDATION.md`, `RUN_IN_ORDER.md`,
  `ai_transcripts/README.md`, `docs/README.md`, `docs/submission/README.md`.
- Added **22 documentation/evidence files**: the three requested audit reports;
  14 JSON/text evidence files in `docs/release_evidence/phase2/`; canonical print
  HTML/PDF; and three archival files (archive index and both exact prior Notes
  copies). No Python implementation/helper was added to the project.
- Both archived Notes copies match their pre-change hashes. Assignment, supporting
  revised Notes, old preview PDF, synthetic dialogue and knowledge base are unchanged.
- **101 local Markdown links checked, zero missing targets**. External share links
  cannot be checked because originals/URLs are absent; fragment anchors were not
  separately parsed. Directory targets are valid navigation links.
- `git diff --no-index --check` against pre-change backups or `/dev/null` emitted
  no whitespace/conflict-marker errors in edited/new Markdown. Normal Git status,
  `git diff --check` and cached checks are unavailable without `.git`; no index or
  Git history was created. No commit/push/remote changes occurred.
- New/edited text was additionally checked for common credential tokens, private-key
  headers and absolute home paths: no matches. Final PDF has no machine-local URI
  annotations. Pattern scans and synthetic-data status do not clear absent originals.

**Required next action:** provide authentic complete AI exports and verified applicable
share links, then review the actual Git candidate contents and decide separately how
to use the intended repository history. Optional clean-install/clean-clone verification
and production work remain separately scoped. Local validation has no unresolved
execution failure; missing AI provenance is the release-submission blocker.

**RELEASE_READY_PENDING_AI_EXPORTS**


## Provenance follow-up — 15 October 2026

The developer supplied original ChatGPT **Conversation 01**, now indexed with its
full share URL in [AI provenance](../ai_transcripts/README.md). Developer-attested
original provenance is recorded separately from independent verification. Expected
export: `ApTap_Original_Chat_01.pdf` (**PENDING; absent**). Conversation date and
content completeness remain unknown; no replacement PDF or conversation was created.

Independent accessibility is **UNVERIFIED**: the web reader returned a content-size
limit (`4194305+`), and Python HTTPS failed local certificate-chain validation.
These tool limitations do not establish that the shared conversation is inaccessible.
Next action: manually verify the shared page and supply the complete native export;
then match content, inventory all other conversations and add genuine coding-agent
histories. The reconstruction remains in `supplementary/` and all existing transcript
and protected application/data/state files are untouched. Earlier execution metrics
and validation results are unchanged; no runtime rerun was needed for this index update.

**RELEASE_READY_PENDING_AI_EXPORTS**
