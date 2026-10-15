"""Stream immutable bank file into line-numbered JSON staging for distributed PySpark.

Bounded memory: avoids whole-file driver materialisation. For production, this pre-ingest
transform is typically implemented in the bank's approved gateway or transfer service.
"""
import argparse
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.ingest import declared_contract, sha256_file, stable_hash


def stage(source:Path, dest:Path, bank_id='APTAP_SYNTHETIC'):
    schema, period=declared_contract(source)
    digest=sha256_file(source)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('w',encoding='utf-8') as sink:
        if schema=='csv_v1':
            with source.open(encoding='utf-8-sig',newline='') as handle:
                records=((num,json.dumps(row,ensure_ascii=False))
                         for num,row in enumerate(csv.DictReader(handle),2))
                _write(records,sink,source,digest,schema,period,bank_id)
        else:
            with source.open(encoding='utf-8-sig') as handle:
                _write(((num,line.rstrip('\n')) for num,line in enumerate(handle,1)),
                       sink,source,digest,schema,period,bank_id)
    return dest


def _write(rows,sink,path,digest,schema,period,bank):
    for num,raw in rows:
        sink.write(json.dumps({'bank_id':bank,'source_file':path.name,'source_sha256':digest,
            'source_line':num,'source_period':period,'schema_version':schema,
            'raw_record_id':stable_hash(['raw_record_v1',stable_hash(['batch_v1',bank,'TRANSACTIONS',digest]),num]),
            'raw_json':raw},ensure_ascii=False,separators=(',',':'))+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--bank-id',default='APTAP_SYNTHETIC')
    args=p.parse_args()
    print(stage(args.source,args.destination,args.bank_id))
