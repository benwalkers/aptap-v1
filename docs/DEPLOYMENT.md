# Deployment design and honest implementation boundary

## Three execution profiles

| Profile | Status in this archive | Runtime |
|---|---|---|
| Local incremental | **Executed and tested** | Python 3.11 standard library + SQLite WAL/ACID |
| Offline container | Build definition present, **Docker runtime unavailable here** | Python 3.11 image, mounted source/working directories |
| Distributed reference | PySpark transform / Iceberg MERGE **not executed here** | Bank-approved Spark + matching Iceberg runtime/catalog |

The local engine is an actual persistent incremental implementation, **not a Spark/Iceberg implementation**. It keeps already committed source digests, hashes transaction identity + canonical payload, and commits each newly found batch atomically. Replaying an identical input does not duplicate Silver, rejects, or manifest entries. Replaced filenames with new bytes are versioned under a new content digest. New IDs are inserted, duplicate payloads audited, and valid corrected payloads replace active records with full superseded-row lineage; no deletion inference or authoritative version ordering is possible.

## AWS reference

- Bank/source gateway lands files into encrypted, private, versioned S3 Bronze using multipart uploads, source-side checksums and delivery-completion manifest. Never process a half-uploaded object.
- Orchestrate per-bank batches with Step Functions or an approved scheduler. The orchestration control state must enforce one *active* batch per bank/feed and durable recovery checkpoints.
- Use an AWS Glue/EMR Spark environment with an explicitly configured Iceberg catalog; upload this project's `spark_jobs/silver_incremental.py` and approved dependencies to artifact storage. The reference job is **not** the end-to-end production implementation: it still requires a transactional manifest protocol, idempotent quarantine writes, partition/rewrite benchmarks, and customer-window feature recomputation.
- `infrastructure/aws/bronze_buckets.yaml` provides a minimal CloudFormation starting point for S3, not a deployed service. Complete with KMS CMKs, IAM least privilege, VPC endpoints, monitoring, account tagging, retention and approved security controls.
- Use partitioning by `bank_id` and `booking_month`, target healthy Parquet file size/compaction, avoid one partition per customer, cluster by customer access patterns, and recompute affected customer-period windows only.
- Never invoke MiniLM on all transactions. Extract distinct merchant/product-context keys, classify them in a bank-scoped versioned registry, and distributed-join back to Silver.

## Inside the bank

- Package only an approved runtime and dependencies. If arbitrary installations are disallowed, deploy the job to the bank's existing Spark/SQL infrastructure, not a new unapproved container.
- No customer raw data leaves the bank. Signed offline model artifacts travel **into** the bank after approvals; enforce no network egress during inference.
- Replace fragile monolithic file uploads with resumable multipart chunk transfers, per-chunk SHA-256, server-side assembly verification, and an atomic READY manifest. An interrupted upload resumes from verified chunks.
- Bank change control gates adapter schema updates, taxonomy changes, models, data retention and rollback. Unversioned source corrections require an explicit bank-approved delivery-order policy and correction audits.

## Volume, capacity and indicative compute cost

Synthetic September: 44,950 transactions for 1,500 customers, 6.46 MB JSONL. Extrapolating that exact density to 15 million customers gives **449.5 million transactions/month**, approximately **64.6 GB raw JSONL**. Actual production records, delivery frequency, distributions and data skew are unknown.

Measured Release 2 local fresh load: approximately 8.5 seconds and 41.3 MiB RSS for three sample months in this build environment; see `outputs/run_metrics.json` for the latest run, which may be an idempotent rerun. Multiplying time by 450M / 135,155 ≈ 3,329 gives about 7.8 hours, but this is not a viable SLA and ignores disk, partition skew and network/shuffle costs. Treat naive linear scaling of the local run as a lower-fidelity *planning scenario*, not a distributed throughput benchmark. Sorting/joining/compaction and storage access can dominate actual costs.

For illustration only, if a 450M-transaction batch consumed **16 AWS Glue DPUs for four hours** at an *assumed* $0.44/DPU-hour, job compute would be $28.16 or roughly **$0.063 per million transactions**. This is **not a quoted AWS price or a measured workload result** and excludes object storage, S3 requests, model CPU, orchestration, KMS, metrics and human reviews. Replace both DPU-hours and unit prices with measured deployment values before sending commercial estimates.

## Spark reference limitations (important)

`./scripts/make_bronze_stage.py` converts a registered immutable raw file into line-numbered NDJSON records suitable for parallel Spark transformation without loading the complete file into memory. The reference Spark worker normalises, detects potential conflicts and demonstrates an Iceberg MERGE **with different CDC semantics from local Release 2**, but is **not tested in this environment**. Missing production work includes: validated match of Python/Spark hash parity, resilient checkpoint ownership, same-batch duplicate quarantine accounting, exactly-once rejected-row publication, backfills, provenance of all noninserted rows, and incremental Gold computation. The local profile demonstrates those first-stage semantics for the synthetic data without claiming Spark parity.
