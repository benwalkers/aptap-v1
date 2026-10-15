# Native execution from the project root — Release 2

Use Python 3.11+ from the directory containing `run_all.sh` and the supplied `data/`:

```bash
bash scripts/workflows/00_setup_venv.sh
bash run_all.sh
```

The setup installs local test/evaluation dependencies. The exact end-to-end workflow
order is source EDA (01), pipeline (03), categoriser (04), classifier benchmark (05),
merchant governance (12), conservative scenario (13), PR evaluation (14), dashboard
(15), tests (02), and rerun verification (06). Governance tests depend on those
previously generated outputs. The standard-library pipeline alone is:

```bash
.venv/bin/python -m pipeline data/
```

**Current verification:** this workflow exited 0 in a disposable fresh-state copy on
15 October 2026, collecting/passing 54 tests and confirming four CSV hashes on replay.
See [release readiness](docs/RELEASE_READINESS_AUDIT.md) for environment, timings,
logs, schemas and source/byte-preservation evidence. No fresh dependency installation
was performed in that audit; it used independently copied installed packages.

## Adding October and replaying safely

Copy the real employer `transactions_2026_10.jsonl` (not supplied) beside September
in `data/`, preserve existing source files/state, and run the same pipeline command.
Check `outputs/run_metrics.json` for `as_of: 2026-10-31`, reconciliation and updated
candidate counts. Then rerun unchanged and verify hashes:

```bash
bash scripts/workflows/06_verify_rerun.sh
```

For an explicit cutoff: `.venv/bin/python -m pipeline data/ --as-of 2026-09-30`.
For the isolated synthetic October demonstration:

```bash
bash scripts/workflows/07_optional_october_demo.sh
```

The demonstration writes under `work/demo_october/` using separate data/state/output.
It passed in the disposable audit copy; it does not prove the unseen employer file.

The local folder contains persistent `work/` and optional weights. Preserve these
for local reruns; **exclude them from Git/release packaging** per the
[packaging checklist](docs/GIT_PACKAGING_CHECKLIST.md). A fresh clone should create
its own state; never copy Release 1 SQLite into Release 2. Earlier ZIP-specific
folder names/state-absence statements are historical packaging descriptions.

## Evidence and provenance

Both bill and switch validation run automatically in the pipeline before Gold
publication. Review [bill validation](docs/BILL_EVIDENCE_VALIDATION.md),
[switch validation](docs/SWITCH_EVIDENCE_VALIDATION.md), `outputs/bill_evidence.csv`,
`outputs/switch_evidence.csv` and their JSON summaries. Candidates are not externally
confirmed contracts, cancellations or savings. Default execution requires no MiniLM.

Complete original AI conversation exports, applicable verified share URLs and all
coding-agent sessions remain missing; see [AI provenance](ai_transcripts/README.md).
