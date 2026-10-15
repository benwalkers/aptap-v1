# Bank-hosted release admission checklist

Before installation, obtain the bank's explicit approval for the following controls.

- [ ] Approved runtime: Spark/Python/container allowed, approved artifact repository, signed builds.
- [ ] Approved disk and object-storage locations, encryption keys, identity and access permissions.
- [ ] Local MiniLM assets licensed, validated, malware scanned, loaded with network disabled.
- [ ] Customer identifiers and bank narrative treated as bank-confidential; no external API calls.
- [ ] Multipart/resumable transfers with checksums and completion manifests to avoid large-upload timeouts.
- [ ] Transaction ID namespace, correction semantics and source sequencing signed off by bank.
- [ ] Data quality thresholds, classification `unknown` policy and human review roles agreed.
- [ ] Tested historical reload and rollback against a fixed Iceberg snapshot and model catalogue version.
- [ ] Change request, performance test, operational runbook, evidence retention and data deletion schedule.
- [ ] Egress-denial test, dependency SBOM and images approved by change board.

Nothing in this ZIP has been deployed inside a bank. These are prerequisites, not completed approvals.
