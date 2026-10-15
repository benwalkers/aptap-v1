"""Exploratory leave-one-descriptor-out lexical and optional MiniLM benchmark.

No train/test merchant family separation is possible reliably for some rare classes;
do NOT promote to production or calibrate a confidence threshold from this experiment.
"""
import argparse
import csv
import json
import math
import os
import re
import statistics
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from categorise.core import CATEGORIES, CORRECTIONS, canonical, ngrams


def evaluate(labels, scores, classes):
    pred=[max(row,key=row.get) for row in scores]
    stats={}
    for cls in classes:
        tp=sum(a==cls and b==cls for a,b in zip(labels,pred))
        fp=sum(a!=cls and b==cls for a,b in zip(labels,pred))
        fn=sum(a==cls and b!=cls for a,b in zip(labels,pred))
        prec=tp/(tp+fp) if tp+fp else 0
        rec=tp/(tp+fn) if tp+fn else 0
        f1=2*prec*rec/(prec+rec) if prec+rec else 0
        stats[cls]={'support':sum(c==cls for c in labels),'precision':round(prec,3),'recall':round(rec,3),'f1':round(f1,3)}
    return {'accuracy':round(sum(a==b for a,b in zip(labels,pred))/len(labels),3),
            'macro_f1':round(statistics.mean(v['f1'] for v in stats.values()),3),'per_category':stats}


def lexical(rows):
    categories=sorted(CATEGORIES)
    data=[]
    for i,(query,truth) in enumerate(rows):
        refs=[(description,category) for j,(description,category) in enumerate(rows) if j!=i]
        corpus=[ngrams(d) for d,c in refs]
        document_freq=Counter()
        for v in corpus:document_freq.update(v.keys())
        idf={k:math.log((len(refs)+1)/(n+1))+1 for k,n in document_freq.items()}
        def encode(v):
            weighted={k:(1+math.log(count))*idf.get(k,0) for k,count in v.items() if k in idf}
            norm=math.sqrt(sum(w*w for w in weighted.values())) or 1
            return {k:w/norm for k,w in weighted.items()}
        x=encode(ngrams(query))
        scores={cat:0. for cat in categories}
        for v,(_,cat) in zip(corpus,refs):
            ref=encode(v)
            similarity=sum(value*ref.get(k,0.) for k,value in x.items())
            scores[cat]=max(scores[cat],similarity)
        data.append(scores)
    return data


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--labels',type=Path,default=Path('data/merchant_labels.csv'))
    p.add_argument('--with-minilm',action='store_true')
    p.add_argument('--model-path',type=Path,default=Path('models/minilm'))
    p.add_argument('--output',type=Path,default=Path('outputs/classifier_benchmark.json'))
    a=p.parse_args()
    with a.labels.open(encoding='utf-8-sig',newline='') as source:
        labels=[(canonical(r['description']),CORRECTIONS.get(canonical(r['description']),r['category'])) for r in csv.DictReader(source)]
    gold=[cat for _,cat in labels]
    results={'char_tfidf':evaluate(gold,lexical(labels),sorted(CATEGORIES))}
    if a.with_minilm:
        os.environ['HF_HUB_OFFLINE']='1'
        from sentence_transformers import SentenceTransformer
        model=SentenceTransformer(str(a.model_path.resolve()),local_files_only=True,device='cpu')
        vectors=model.encode([d for d,_ in labels],normalize_embeddings=True)
        semantic=[]
        for i in range(len(labels)):
            scores={c:-1. for c in sorted(CATEGORIES)}
            for j,(_,cat) in enumerate(labels):
                if i==j:continue
                scores[cat]=max(scores[cat],float(vectors[i]@vectors[j]))
            semantic.append(scores)
        results['minilm']=evaluate(gold,semantic,sorted(CATEGORIES))
    report={'n':len(labels),'method':'leave-one-description-out',
           'limitations':'Related merchant families remain across folds; rare classes are too small for reliable calibration or PR curves.',
           'models':results}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    for key,val in results.items():print(key,val['accuracy'],val['macro_f1'])
if __name__=='__main__':main()
