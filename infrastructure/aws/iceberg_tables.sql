-- REFERENCE DDL: requires a configured Spark+Iceberg catalog named lake.
-- SQL engine/platform compatibility must be verified before deployment.
CREATE NAMESPACE IF NOT EXISTS lake.silver;
CREATE NAMESPACE IF NOT EXISTS lake.quality;
CREATE TABLE IF NOT EXISTS lake.silver.transactions (
  transaction_key STRING, bank_id STRING, transaction_id STRING,
  customer_id STRING, booking_date DATE, amount DECIMAL(18,2),
  currency STRING, description STRING, payload_hash STRING,
  source_sha256 STRING, raw_record_id STRING
) USING iceberg PARTITIONED BY (bank_id, months(booking_date));
CREATE TABLE IF NOT EXISTS lake.quality.rejected_rows (
  raw_record_id STRING, reason STRING, raw_json STRING
) USING iceberg;
CREATE TABLE IF NOT EXISTS lake.quality.mutation_conflicts (
  raw_record_id STRING, transaction_key STRING, raw_json STRING, payload_hash STRING
) USING iceberg;
