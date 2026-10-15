"""Non-destructive source EDA: strict schema-aware date audit and file digests."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.ingest import declared_contract, input_files, parse_date, sha256_file


def audit_one(path: Path):
    schema, period = declared_contract(path)
    months = Counter()
    anomalies = Counter()
    fields = set()
    total = 0
    if schema == 'csv_v1':
        with path.open(encoding='utf-8-sig', newline='') as fh:
            iterator = csv.DictReader(fh)
            for row in iterator:
                total += 1
                fields.update(row)
                date = row.get('booking_date')
                try:
                    iso = parse_date(date, schema)
                    months[iso[:7]] += 1
                    if iso[:7] != period:
                        anomalies['cross_period_booking_date'] += 1
                except ValueError:
                    anomalies['invalid_date'] += 1
    else:
        with path.open(encoding='utf-8-sig') as fh:
            for line in fh:
                total += 1
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError('not object')
                    fields.update(row)
                    iso = parse_date(row.get('posted'), schema)
                    months[iso[:7]] += 1
                    if iso[:7] != period:
                        anomalies['cross_period_booking_date'] += 1
                except (ValueError, TypeError, json.JSONDecodeError):
                    anomalies['invalid_date_or_json'] += 1
    return dict(file=path.name, schema=schema, declared_period=period,
                records=total, sha256=sha256_file(path), fields=sorted(fields),
                booking_months=dict(sorted(months.items())), issues=dict(anomalies))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', type=Path, default=Path('data'))
    ap.add_argument('--output', type=Path, default=Path('outputs/source_eda.json'))
    args = ap.parse_args()
    report={'files': [audit_one(p) for p in input_files(args.data_dir)]}
    report['records_total']=sum(x['records'] for x in report['files'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n',encoding='utf-8')
    for row in report['files']:
        print(f"{row['file']} [{row['schema']}]: {row['records']:,} records, booking months {row['booking_months']}, issues {row['issues']}")
    print('Input EDA:', args.output)

if __name__=='__main__':
    main()
