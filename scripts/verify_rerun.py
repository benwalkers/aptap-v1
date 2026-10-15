"""Verify exact output hashes and no newly committed batches on repeated input."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

CSV_NAMES = ('clean_transactions.csv', 'rejected_rows.csv',
             'recurring_bills.csv', 'switches.csv')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--as-of',default=None)
    p.add_argument('--engine',choices=['lexical','minilm','auto'],default='lexical')
    p.add_argument('--output-dir',type=Path,default=Path('outputs'))
    args=p.parse_args()
    baseline={name:sha(args.output_dir/name) for name in CSV_NAMES}
    command=[sys.executable,'-m','pipeline','data/','--engine',args.engine]
    if args.as_of is not None:command += ['--as-of',args.as_of]
    subprocess.run(command,check=True)
    current={name:sha(args.output_dir/name) for name in CSV_NAMES}
    metrics=json.loads((args.output_dir/'run_metrics.json').read_text())
    unchanged=baseline==current
    no_new_batches=metrics['new_batches']==0
    result={'same_four_csv_hashes':unchanged,'new_batches':metrics['new_batches'],
            'no_new_batches':no_new_batches,'files':
            {name:{'before':baseline[name],'after':current[name]} for name in CSV_NAMES}}
    dest=args.output_dir/'workflow_rerun_verification.json'
    dest.write_text(json.dumps(result, indent=2)+'\n')
    print('Rerun verification:',dest)
    if not (unchanged and no_new_batches):
        raise SystemExit('FAILED: unexpected new batch or output hash change')
    print('PASS: 4 CSVs byte-identical; 0 new batches')

if __name__=='__main__':
    main()
