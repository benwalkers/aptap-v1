"""Spark/Iceberg reference: normalise line-numbered Bronze and MERGE new transactions.

Requires PySpark 4.x and a separately configured Iceberg catalog (not provided by pip
alone). Not executed by local smoke tests. See docs/DEPLOYMENT.md.

Call: spark-submit ... spark_jobs/silver_incremental.py --stage-uri s3://.../stage/
--silver-table lake.silver.transactions --reject-table lake.quality.rejected_rows
--conflict-table lake.quality.mutation_conflicts

Source rows should be copied immutably BEFORE invoking this job. Atomic file-level
checkpoints and batch orchestration belong to the approved Iceberg/control service.
"""
from __future__ import annotations
import argparse
from pyspark.sql import SparkSession, functions as F, Window
from pyspark.sql.types import StructType, StructField, StringType, LongType

STAGE=StructType([
    StructField('bank_id',StringType(),False),
    StructField('source_file',StringType(),False),
    StructField('source_sha256',StringType(),False),
    StructField('source_line',LongType(),False),
    StructField('source_period',StringType(),False),
    StructField('schema_version',StringType(),False),
    StructField('raw_record_id',StringType(),False),
    StructField('raw_json',StringType(),False),
])


def prepare(stage):
    raw=stage.withColumn('obj',F.from_json('raw_json','map<string,string>'))
    v1=F.col('schema_version')=='csv_v1'
    key=lambda a,b:F.when(v1,F.col('obj').getItem(a)).otherwise(F.col('obj').getItem(b))
    amount=key('amount','value')
    monetary=F.regexp_replace(F.trim(amount),'[£,]','')
    valid_numeric=monetary.rlike(r'^[+-]?\d+(?:\.\d{1,2})?$')
    magnitude=F.when(valid_numeric,monetary.cast('decimal(18,2)'))
    direction=F.upper(F.trim(F.col('obj').getItem('direction')))
    iso=F.trim(key('booking_date','posted'))
    # Date-only values. No implicit locale, no fabricated timezone.
    date_v1=F.try_to_timestamp(F.when(iso.rlike(r'^\d{4}-\d{2}-\d{2}$'),iso),F.lit('yyyy-MM-dd')).cast('date')
    date_v2=F.coalesce(
        F.try_to_timestamp(F.when(iso.rlike(r'^\d{2}/\d{2}/\d{4}$'),iso),F.lit('dd/MM/yyyy')).cast('date'),
        F.try_to_timestamp(F.when(iso.rlike(r'^\d{4}-\d{2}-\d{2}$'),iso),F.lit('yyyy-MM-dd')).cast('date'))
    result=(raw.withColumn('transaction_id',F.trim(key('transaction_id','txn_id')))
       .withColumn('customer_id',F.trim(key('customer_id','cust_ref')))
       .withColumn('booking_date',F.when(v1,date_v1).otherwise(date_v2))
       .withColumn('currency',F.upper(F.trim(F.when(v1,F.col('obj').getItem('currency'))
                                 .otherwise(F.coalesce(F.col('obj').getItem('currency'),F.lit('GBP'))))))
       .withColumn('description',F.upper(F.regexp_replace(F.trim(key('description','narrative')),r'\s+',' ')))
       .withColumn('amount',F.when(v1,magnitude)
          .otherwise(F.when(direction=='DEBIT',-magnitude).otherwise(magnitude)))
    )
    invalid=F.when(F.col('obj').isNull(),'INVALID_JSON_RECORD')
    invalid=invalid.when(F.col('transaction_id').isNull() | (F.col('transaction_id')==''),'MISSING_TRANSACTION_ID')
    invalid=invalid.when(F.col('customer_id').isNull() | (F.col('customer_id')==''),'MISSING_CUSTOMER_ID')
    invalid=invalid.when(F.col('booking_date').isNull(),'INVALID_BOOKING_DATE')
    invalid=invalid.when(F.col('description').isNull() | (F.col('description')==''),'MISSING_DESCRIPTION')
    invalid=invalid.when(F.coalesce(F.col('currency')!='GBP',F.lit(True)),'UNSUPPORTED_CURRENCY')
    invalid=invalid.when((~v1)&(~direction.isin('DEBIT','CREDIT')),'INVALID_DIRECTION')
    invalid=invalid.when((~v1)&(magnitude < 0),'NEGATIVE_JSON_MAGNITUDE')
    invalid=invalid.when(F.col('amount').isNull(),'INVALID_AMOUNT')
    result=result.withColumn('reason',invalid)
    valid=result.filter(F.col('reason').isNull())
    valid=(valid.withColumn('transaction_key',F.sha2(F.to_json(F.array(
                F.lit('transaction_key_v1'),F.col('bank_id'),F.col('transaction_id'))),256))
        .withColumn('payload_hash',F.sha2(F.to_json(F.array(
                F.lit('payload_v1'),F.col('customer_id'),
                F.date_format('booking_date','yyyy-MM-dd'),
                F.col('amount').cast('string'),F.col('currency'),F.col('description'))),256)))
    return valid,result.filter(F.col('reason').isNotNull())


def merge_batch(spark,stage_uri,silver_table,reject_table,conflict_table):
    staged=spark.read.schema(STAGE).json(stage_uri)
    valid,invalid=prepare(staged)
    # Deterministic priority by source identity within a batch.
    order=Window.partitionBy('transaction_key').orderBy('source_sha256','source_line')
    valid=valid.withColumn('_rank',F.row_number().over(order))
    first=valid.filter('_rank=1').drop('_rank')
    repeated=valid.filter('_rank>1')
    target=spark.table(silver_table).select('transaction_key','payload_hash')
    # Renaming avoids ambiguity in Spark joins; explicit anti-join is robust.
    target_ref=target.select('transaction_key',F.col('payload_hash').alias('existing_hash'))
    joined=first.join(target_ref,'transaction_key','left')
    new=joined.filter(F.col('existing_hash').isNull()).drop('existing_hash')
    conflicts=joined.filter(F.col('existing_hash').isNotNull() &
                            (F.col('payload_hash')!=F.col('existing_hash')))
    # Within-batch duplicates with different payloads are conflicts, never last-write-wins.
    dup_conflicts=(repeated.join(first.select('transaction_key',F.col('payload_hash').alias('first_hash')),'transaction_key')
                   .filter(F.col('payload_hash')!=F.col('first_hash')))
    all_conflicts=conflicts.select('raw_record_id','transaction_key','raw_json','payload_hash').unionByName(
        dup_conflicts.select('raw_record_id','transaction_key','raw_json','payload_hash'))
    conflict_keys=all_conflicts.select('transaction_key').distinct()
    new=new.join(conflict_keys,'transaction_key','left_anti')
    # Idempotent inserts; production scheduler must commit and reconcile a manifest
    # under an approved transactional/checkpoint protocol around these writes.
    new.createOrReplaceTempView('_aptap_new_transactions')
    spark.sql(f'''MERGE INTO {silver_table} AS t USING _aptap_new_transactions AS s
      ON t.transaction_key=s.transaction_key
      WHEN NOT MATCHED THEN INSERT (transaction_key,bank_id,transaction_id,customer_id,
      booking_date,amount,currency,description,payload_hash,source_sha256,raw_record_id)
      VALUES (s.transaction_key,s.bank_id,s.transaction_id,s.customer_id,
      s.booking_date,s.amount,s.currency,s.description,s.payload_hash,s.source_sha256,s.raw_record_id)''')
    invalid.select('raw_record_id','reason','raw_json').writeTo(reject_table).append()
    all_conflicts.writeTo(conflict_table).append()
    return {'scope':'reference_job','note':'manifest checkpoint + replay-safe reject writes must be added by target orchestrator'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stage-uri',required=True)
    p.add_argument('--silver-table',required=True)
    p.add_argument('--reject-table',required=True)
    p.add_argument('--conflict-table',required=True)
    a=p.parse_args()
    spark=SparkSession.builder.appName('aptap-silver-incremental').getOrCreate()
    merge_batch(spark,a.stage_uri,a.silver_table,a.reject_table,a.conflict_table)

if __name__=='__main__':main()
