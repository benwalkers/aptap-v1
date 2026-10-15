"""Incremental file-batch ingestion: immutable original, atomic checkpoint, canonical CDC-style keys.

Runs using Python stdlib + SQLite for reproducible local execution. Production Spark/Iceberg
profile is documented separately; this module does NOT claim that SQLite is distributed.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

CSV_FIELDS = {'transaction_id', 'customer_id', 'booking_date', 'amount', 'currency', 'description'}
JSON_FIELDS = {'txn_id', 'cust_ref', 'posted', 'value', 'direction', 'narrative'}
FILENAME = re.compile(r'^transactions_(\d{4})_(\d{2})\.(csv|jsonl)$')
DATE_FORMATS = {'csv_v1': '%Y-%m-%d', 'jsonl_v2': '%d/%m/%Y'}


def stable_hash(values):
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for piece in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(piece)
    return h.hexdigest()


def input_files(directory: Path):
    paths = sorted([*directory.glob('transactions_*.csv'), *directory.glob('transactions_*.jsonl')])
    if not paths:
        raise FileNotFoundError(f'No transaction files in {directory}')
    for path in paths:
        if not FILENAME.match(path.name):
            raise ValueError(f'INVALID_DELIVERY_FILENAME: {path.name}')
    return paths


def declared_contract(path: Path):
    match = FILENAME.fullmatch(path.name)
    if not match:
        raise ValueError(f'INVALID_DELIVERY_FILENAME: {path.name}')
    period = f'{match.group(1)}-{match.group(2)}'
    if not (1 <= int(match.group(2)) <= 12):
        raise ValueError('INVALID_SOURCE_PERIOD')
    schema = 'csv_v1' if path.suffix == '.csv' else 'jsonl_v2'
    if schema == 'csv_v1':
        with path.open('r', newline='', encoding='utf-8-sig') as source:
            header = next(csv.reader(source), [])
        if len(header) != len(set(header)):
            raise ValueError('DUPLICATE_SOURCE_COLUMNS')
        missing = CSV_FIELDS - set(header)
        if missing:
            raise ValueError(f'MISSING_CSV_HEADERS: {sorted(missing)}')
    return schema, period


def parse_date(value, contract):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('INVALID_BOOKING_DATE')
    raw = value.strip()
    formats = [DATE_FORMATS[contract]]
    # October is declared as the September schema; tolerate explicit ISO date formatting
    # variation only. Day/month interpretation is never guessed.
    if contract == 'jsonl_v2':
        formats.append('%Y-%m-%d')
    for pattern in formats:
        try:
            parsed = dt.datetime.strptime(raw, pattern).date()
            if parsed.strftime(pattern) == raw:
                return parsed.isoformat()
        except ValueError:
            continue
    raise ValueError('INVALID_BOOKING_DATE')


def parse_amount(value):
    if value is None:
        raise ValueError('INVALID_AMOUNT')
    raw = str(value).strip()
    # September contract: GBP magnitudes; allow common UK lexical wrappers, not
    # ambiguous European decimal/grouping or floating-point/scientific notation.
    raw = re.sub(r'^(?:GBP|£)\s*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s*(?:GBP|£)$', '', raw, flags=re.IGNORECASE).strip()
    if re.fullmatch(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?', raw) is None:
        raise ValueError('INVALID_AMOUNT')
    raw = raw.replace(',', '')
    if not re.fullmatch(r'[+-]?\d+(?:\.\d{1,2})?', raw):
        raise ValueError('INVALID_AMOUNT')
    try:
        amount = Decimal(raw)
    except InvalidOperation as ex:
        raise ValueError('INVALID_AMOUNT') from ex
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        raise ValueError('INVALID_AMOUNT')
    return amount.quantize(Decimal('0.01'))


def merchant_key(desc):
    return ' '.join(str(desc or '').strip().upper().split())


def canonical(record, schema, bank_id):
    if not isinstance(record, dict):
        raise ValueError('INVALID_RECORD_SHAPE')
    if schema == 'csv_v1':
        tid, cust = record.get('transaction_id'), record.get('customer_id')
        date = parse_date(record.get('booking_date'), schema)
        amount = parse_amount(record.get('amount'))
        currency = str(record.get('currency') or '').strip().upper()
        desc = record.get('description')
    else:
        missing = JSON_FIELDS - set(record)
        if missing:
            raise ValueError('MISSING_JSON_KEYS:' + ','.join(sorted(missing)))
        tid, cust = record.get('txn_id'), record.get('cust_ref')
        date = parse_date(record.get('posted'), schema)
        amount = parse_amount(record.get('value'))
        direction = str(record.get('direction') or '').strip().upper()
        if direction not in ('CREDIT', 'DEBIT'):
            raise ValueError('INVALID_DIRECTION')
        # A magnitude+direction schema must not quietly accept sign conflicts.
        if amount < 0:
            raise ValueError('NEGATIVE_JSON_MAGNITUDE')
        amount = amount if direction == 'CREDIT' else -amount
        currency = str(record.get('currency') or 'GBP').strip().upper()
        desc = record.get('narrative')
    tid = str(tid or '').strip()
    cust = str(cust or '').strip()
    desc = str(desc or '').strip()
    if not tid:
        raise ValueError('MISSING_TRANSACTION_ID')
    if not cust:
        raise ValueError('MISSING_CUSTOMER_ID')
    if not desc:
        raise ValueError('MISSING_DESCRIPTION')
    if currency != 'GBP':
        raise ValueError('UNSUPPORTED_CURRENCY')
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9_.-]{1,64}', bank_id):
        raise ValueError('INVALID_BANK_ID')
    normalized = merchant_key(desc)
    key = stable_hash(['transaction_key_v1', bank_id, tid])
    payload_hash = stable_hash(['payload_v1', cust, date, format(amount, '.2f'), currency, normalized])
    return {'transaction_key': key, 'bank_id': bank_id, 'transaction_id': tid,
            'customer_id': cust, 'booking_date': date, 'amount': format(amount, '.2f'),
            'currency': currency, 'description': normalized, 'raw_description': desc,
            'description_key': normalized, 'payload_hash': payload_hash}


def source_rows(path, schema):
    if schema == 'csv_v1':
        with path.open(newline='', encoding='utf-8-sig') as source:
            for row_no, row in enumerate(csv.DictReader(source), 2):
                yield row_no, row, None
    else:
        with path.open(encoding='utf-8-sig') as source:
            for row_no, line in enumerate(source, 1):
                if not line.strip():
                    yield row_no, None, line.rstrip('\n')
                    continue
                try:
                    data = json.loads(line, parse_float=Decimal)
                    if not isinstance(data, dict):
                        raise ValueError('JSON_NOT_OBJECT')
                    yield row_no, data, None
                except (ValueError, json.JSONDecodeError):
                    yield row_no, None, line.rstrip('\n')


def connect(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=30000')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS ingestion_manifest (
      batch_id TEXT PRIMARY KEY, bank_id TEXT NOT NULL, feed_id TEXT NOT NULL,
      source_file TEXT NOT NULL, source_period TEXT NOT NULL, schema_version TEXT NOT NULL,
      source_sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, bronze_uri TEXT NOT NULL,
      rows INTEGER NOT NULL, inserted INTEGER NOT NULL, corrected INTEGER NOT NULL DEFAULT 0, duplicates INTEGER NOT NULL,
      invalid INTEGER NOT NULL, conflicts INTEGER NOT NULL, status TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(bank_id,feed_id,source_sha256)
    );
    CREATE TABLE IF NOT EXISTS clean_transactions (
      transaction_key TEXT PRIMARY KEY, bank_id TEXT NOT NULL,
      transaction_id TEXT NOT NULL, customer_id TEXT NOT NULL,
      booking_date TEXT NOT NULL, amount TEXT NOT NULL, currency TEXT NOT NULL,
      description TEXT NOT NULL, raw_description TEXT NOT NULL,
      description_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
      source_batch_id TEXT NOT NULL, source_row INTEGER NOT NULL,
      source_period TEXT NOT NULL, schema_version TEXT NOT NULL,
      source_file TEXT NOT NULL, raw_json TEXT NOT NULL,
      first_ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(source_batch_id) REFERENCES ingestion_manifest(batch_id)
    );
    CREATE INDEX IF NOT EXISTS ix_customer_date ON clean_transactions(bank_id, customer_id, booking_date);
    CREATE INDEX IF NOT EXISTS ix_booking_period ON clean_transactions(booking_date);
    CREATE TABLE IF NOT EXISTS rejected_rows (
      raw_record_id TEXT PRIMARY KEY,
      source_batch_id TEXT NOT NULL,
      source_file TEXT NOT NULL, source_line INTEGER NOT NULL,
      transaction_id TEXT, reason TEXT NOT NULL, raw_json TEXT NOT NULL,
      FOREIGN KEY(source_batch_id) REFERENCES ingestion_manifest(batch_id)
    );
    CREATE TABLE IF NOT EXISTS transaction_corrections (
      correction_id TEXT PRIMARY KEY,
      transaction_key TEXT NOT NULL,
      prior_batch_id TEXT NOT NULL, prior_source_line INTEGER NOT NULL,
      new_batch_id TEXT NOT NULL, new_source_line INTEGER NOT NULL,
      prior_payload_hash TEXT NOT NULL, new_payload_hash TEXT NOT NULL,
      old_customer_id TEXT NOT NULL, new_customer_id TEXT NOT NULL,
      applied_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS source_validation_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_id TEXT, check_name TEXT NOT NULL, severity TEXT NOT NULL,
      observed TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    return conn


def immutable_land(source, bronze_root, bank_id, digest):
    destination = bronze_root / bank_id / digest[:2] / digest / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != digest:
            raise RuntimeError('BRONZE_INTEGRITY_FAILURE')
        return destination
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.landing-', delete=False) as temp:
        partial = Path(temp.name)
        try:
            with source.open('rb') as incoming:
                shutil.copyfileobj(incoming, temp, length=8*1024*1024)
            temp.flush()
            os.fsync(temp.fileno())
        except Exception:
            partial.unlink(missing_ok=True)
            raise
    if sha256_file(partial) != digest:
        partial.unlink(missing_ok=True)
        raise RuntimeError('TRANSFER_CHECKSUM_MISMATCH')
    os.replace(partial, destination)
    return destination


def ingest(input_dir: Path, work_dir: Path, bank_id='APTAP_SYNTHETIC', feed_id='TRANSACTIONS'):
    """Atomic per-file batch commits; repeat runs skip already-committed file digests.

    Returns (store_path, cumulative_counter_dict, run_batch_details).
    """
    db_path = work_dir / 'incremental.sqlite'
    bronze = work_dir / 'bronze'
    conn = connect(db_path)
    processed = []
    try:
        for path in input_files(input_dir):
            schema, period = declared_contract(path)
            digest = sha256_file(path)
            batch = stable_hash(['batch_v1', bank_id, feed_id, digest])
            existing = conn.execute('SELECT status FROM ingestion_manifest WHERE batch_id=?', (batch,)).fetchone()
            if existing and existing[0] == 'COMMITTED':
                processed.append({'file':path.name,'action':'SKIPPED_IDENTICAL','sha256':digest})
                continue
            if existing:
                raise RuntimeError(f'Unexpected incomplete batch {batch}: {existing[0]}')
            landed = immutable_land(path, bronze, bank_id, digest)
            stats = {'rows':0,'inserted':0,'corrected':0,'duplicates':0,'invalid':0,'conflicts':0}
            # Hold the batch in one ACID transaction. Crash before COMMIT => no half-loaded batch.
            conn.execute('BEGIN IMMEDIATE')
            try:
                conn.execute('''INSERT INTO ingestion_manifest
                  (batch_id,bank_id,feed_id,source_file,source_period,schema_version,source_sha256,bytes,bronze_uri,
                   rows,inserted,corrected,duplicates,invalid,conflicts,status)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (batch,bank_id,feed_id,path.name,period,schema,digest,path.stat().st_size,str(landed),0,0,0,0,0,0,'PROCESSING'))
                last_key = (None, None)
                for line, raw, broken in source_rows(landed, schema):
                    stats['rows'] += 1
                    record_id = stable_hash(['raw_record_v1', batch, line])
                    tx = None
                    if raw is None:
                        reason = 'INVALID_JSON_RECORD'
                    else:
                        try:
                            tx = canonical(raw, schema, bank_id)
                            reason = None
                        except ValueError as ex:
                            reason = str(ex)
                    raw_json = json.dumps(raw if raw is not None else broken,
                                          ensure_ascii=False, sort_keys=True, default=str)
                    if tx is not None:
                        matching = conn.execute('''SELECT payload_hash,source_batch_id,source_row,source_file,raw_json,customer_id
                                         FROM clean_transactions WHERE transaction_key=?''',
                                         (tx['transaction_key'],)).fetchone()
                        if matching is None:
                            conn.execute('''INSERT INTO clean_transactions
                            (transaction_key,bank_id,transaction_id,customer_id,booking_date,amount,currency,
                             description,raw_description,description_key,payload_hash,source_batch_id,source_row,
                             source_period,schema_version,source_file,raw_json)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                             (tx['transaction_key'],tx['bank_id'],tx['transaction_id'],tx['customer_id'],tx['booking_date'],
                              tx['amount'],tx['currency'],tx['description'],tx['raw_description'],tx['description_key'],
                              tx['payload_hash'],batch,line,period,schema,path.name,raw_json))
                            stats['inserted'] += 1
                            continue
                        if matching[0] != tx['payload_hash']:
                            # Latest valid observed delivery wins. The previous active source row
                            # becomes a SUPERSEDED rejection, so each raw row is accounted for
                            # exactly once: active Silver OR rejected/superseded audit.
                            old_hash,old_batch,old_line,old_file,old_raw,old_customer = matching
                            old_record = stable_hash(['raw_record_v1',old_batch,old_line])
                            conn.execute('''INSERT INTO rejected_rows
                              (raw_record_id,source_batch_id,source_file,source_line,transaction_id,reason,raw_json)
                              VALUES (?,?,?,?,?,?,?)''',
                              (old_record,old_batch,old_file,old_line,tx['transaction_id'],
                               'SUPERSEDED_BY_CORRECTION',old_raw))
                            correction_id=stable_hash(['correction_v1',old_record,record_id])
                            conn.execute('''INSERT INTO transaction_corrections
                              (correction_id,transaction_key,prior_batch_id,prior_source_line,new_batch_id,
                               new_source_line,prior_payload_hash,new_payload_hash,old_customer_id,new_customer_id)
                              VALUES (?,?,?,?,?,?,?,?,?,?)''',
                              (correction_id,tx['transaction_key'],old_batch,old_line,batch,line,
                               old_hash,tx['payload_hash'],old_customer,tx['customer_id']))
                            conn.execute('''UPDATE clean_transactions SET
                              customer_id=?,booking_date=?,amount=?,currency=?,description=?,raw_description=?,
                              description_key=?,payload_hash=?,source_batch_id=?,source_row=?,source_period=?,
                              schema_version=?,source_file=?,raw_json=? WHERE transaction_key=?''',
                              (tx['customer_id'],tx['booking_date'],tx['amount'],tx['currency'],tx['description'],
                               tx['raw_description'],tx['description_key'],tx['payload_hash'],batch,line,period,
                               schema,path.name,raw_json,tx['transaction_key']))
                            stats['corrected'] += 1
                            if old_customer != tx['customer_id']:
                                conn.execute('''INSERT INTO source_validation_events
                                  (batch_id,check_name,severity,observed) VALUES (?,?,?,?)''',
                                  (batch,'CUSTOMER_REASSIGNMENT','WARNING',tx['transaction_id']))
                            continue
                        reason = 'DUPLICATE_TRANSACTION'
                    reason_type = 'duplicates' if reason == 'DUPLICATE_TRANSACTION' else 'invalid'
                    stats[reason_type] += 1
                    tid = str((raw or {}).get('transaction_id') or (raw or {}).get('txn_id') or '') if isinstance(raw, dict) else ''
                    conn.execute('''INSERT INTO rejected_rows
                        (raw_record_id,source_batch_id,source_file,source_line,transaction_id,reason,raw_json)
                        VALUES (?,?,?,?,?,?,?)''',
                        (record_id,batch,path.name,line,tid,reason,raw_json))
                if stats['rows'] != sum(stats[x] for x in ('inserted','corrected','duplicates','invalid','conflicts')):
                    raise RuntimeError('SOURCE_RECONCILIATION_FAILED')
                conn.execute('''UPDATE ingestion_manifest SET rows=?,inserted=?,corrected=?,duplicates=?,invalid=?,conflicts=?,status='COMMITTED'
                                WHERE batch_id=?''', (stats['rows'],stats['inserted'],stats['corrected'],stats['duplicates'],stats['invalid'],stats['conflicts'],batch))
                prior_versions = conn.execute('''SELECT COUNT(*) FROM ingestion_manifest
                  WHERE bank_id=? AND feed_id=? AND source_file=? AND batch_id<>? AND status='COMMITTED' ''',
                  (bank_id,feed_id,path.name,batch)).fetchone()[0]
                if prior_versions:
                    conn.execute('''INSERT INTO source_validation_events (batch_id,check_name,severity,observed)
                      VALUES (?,?,?,?)''', (batch,'SOURCE_FILENAME_REUSED','WARNING',str(prior_versions)))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            processed.append({'file':path.name,'action':'COMMITTED','sha256':digest,**stats})
        row = conn.execute('''SELECT COALESCE(SUM(rows),0),COALESCE(SUM(inserted),0),
          COALESCE(SUM(corrected),0),COALESCE(SUM(duplicates),0),
          COALESCE(SUM(invalid),0),COALESCE(SUM(conflicts),0)
          FROM ingestion_manifest WHERE status='COMMITTED' AND bank_id=? AND feed_id=?''',
          (bank_id,feed_id)).fetchone()
        total, inserted, corrected, duplicates, invalid, conflicts = row
        clean_count = conn.execute('SELECT COUNT(*) FROM clean_transactions WHERE bank_id=?',(bank_id,)).fetchone()[0]
        reject_count = conn.execute('''SELECT COUNT(*) FROM rejected_rows r JOIN ingestion_manifest m
              ON m.batch_id=r.source_batch_id WHERE m.bank_id=? AND m.feed_id=?''',
              (bank_id,feed_id)).fetchone()[0]
        superseded = conn.execute('''SELECT COUNT(*) FROM rejected_rows r JOIN ingestion_manifest m
              ON m.batch_id=r.source_batch_id
              WHERE m.bank_id=? AND m.feed_id=? AND r.reason='SUPERSEDED_BY_CORRECTION' ''',
              (bank_id,feed_id)).fetchone()[0]
        if total != clean_count + reject_count or clean_count != inserted or \
                reject_count != duplicates + invalid + conflicts + superseded or superseded != corrected:
            raise RuntimeError(f'CUMULATIVE_RECONCILIATION_FAILED raw={total} clean={clean_count} rejected={reject_count} corrected={corrected}')
        return db_path, {'raw':total,'clean':clean_count,'rejected':reject_count,
                         'duplicates':duplicates,'invalid':invalid,'conflicts':conflicts,
                         'corrected':corrected,'superseded':superseded}, processed
    finally:
        conn.close()
