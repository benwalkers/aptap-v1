#!/usr/bin/env python3
"""Build offline Plotly classification-risk dashboard from existing ApTap outputs."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard.build import produce

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--with-minilm',action='store_true',help='Use existing locally provisioned MiniLM for diagnostic comparisons (offline)')
    args=p.parse_args()
    produce(with_minilm=args.with_minilm)
