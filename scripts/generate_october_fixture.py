"""Create a sample extra October file for manually exercising reruns.

Run with --output tests/fixtures/transactions_2026_10.jsonl, then copy to data/ only
when you intend to alter the run input. Not included by default in actual data/.
"""
import argparse
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument("--output",default="tests/fixtures/transactions_2026_10.jsonl")
args=parser.parse_args()
output=Path(args.output)
output.parent.mkdir(parents=True,exist_ok=True)
records=[
    {"txn_id":"T48807160","cust_ref":"C00710","posted":"05/07/2026","value":"£66.73","direction":"DEBIT","narrative":"tesco pfs 4021","new_bank_field":"ABC"},
    {"txn_id":"OCT_DEMO_0001","cust_ref":"C00710","posted":"04/10/2026","value":"£40.20","direction":"DEBIT","narrative":"OCTOPUS ENERGY LTD","new_bank_field":"ABC"},
    {"txn_id":"OCT_DEMO_BAD","cust_ref":"","posted":"04/10/2026","value":"£10.20","direction":"DEBIT","narrative":"UNKNOWN"}
]
output.write_text("\n".join(json.dumps(r) for r in records)+"\n")
print(f"Wrote optional test fixture: {output} (do not mix with supplied original files for baseline)")
