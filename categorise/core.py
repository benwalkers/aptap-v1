"""Offline selective categoriser. No external service calls and no uncalibrated auto-approval.

Data disclaimer: curated aliases are explicitly DEMO-reviewed assumptions, not bank approval.
"""
from __future__ import annotations
import csv
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CATEGORIES = {'broadband','energy','mobile','car_insurance','home_insurance','water',
              'streaming','gym','council_tax','not_a_bill'}
SYSTEM_OUTCOME = 'REVIEW_REQUIRED'  # internal review status, NOT a scored category
CORRECTIONS = {'TESCO MOBILE':'mobile','OCTOPUS ENERGY':'energy'}


def canonical(text):
    return ' '.join(str(text or '').strip().upper().split())


def ngrams(text):
    counts=Counter()
    for token in re.findall(r'[A-Z0-9]+',canonical(text)):
        padded=f' {token} '
        for n in (2,3,4,5):
            counts.update(padded[i:i+n] for i in range(len(padded)-n+1))
    return counts


@dataclass(frozen=True)
class Result:
    category: str
    provider_id: str|None
    method: str
    score: float|None
    needs_review: bool
    usable_for_switches: bool
    candidate_category: str|None = None
    matched_reference: str|None = None
    status: str = 'REVIEW_REQUIRED'


class MerchantCategoriser:
    def __init__(self, labels_path='data/merchant_labels.csv', engine='auto',
                 model_path='models/minilm', aliases_path='classification/curated_aliases.csv'):
        if engine not in ('auto','lexical','minilm'):
            raise ValueError('Unsupported engine')
        self.engine=engine
        self.model_path=Path(model_path)
        self.approved={}
        # Original labels are evidence and proposal input, NEVER unconditional accepted truth.
        self.labels={}
        with Path(labels_path).open(encoding='utf-8-sig',newline='') as source:
            for row in csv.DictReader(source):
                desc=canonical(row['description'])
                self.labels[desc]=CORRECTIONS.get(desc,row['category'].strip())
        with Path(aliases_path).open(encoding='utf-8-sig',newline='') as source:
            for row in csv.DictReader(source):
                desc=canonical(row['description'])
                cat=row['category'].strip()
                if cat not in CATEGORIES: raise ValueError(f'Unknown category in registry: {cat}')
                if desc in self.approved: raise ValueError(f'Duplicate alias {desc}')
                self.approved[desc]=(cat,row['provider_id'].strip() or None,row['review_status'])
        self.examples=list(dict.fromkeys([*self.approved,*self.labels]))
        self.example_categories=[self.approved[x][0] if x in self.approved else self.labels[x] for x in self.examples]
        self._char_vectors=[ngrams(x) for x in self.examples]
        df=Counter()
        for v in self._char_vectors:df.update(v.keys())
        count=len(self.examples)
        self._idf={k:math.log((count+1)/(n+1))+1 for k,n in df.items()}
        self._vectors=[self._normalize(v) for v in self._char_vectors]
        self._model=None
        self._reference_embeddings=None
        self.semantic_available=(self.model_path/'modules.json').exists()
        if engine=='minilm' and not self.semantic_available:
            raise FileNotFoundError(f'No offline MiniLM at {self.model_path}: run scripts/download_model.py')

    def _normalize(self,vec):
        values={k:(1+math.log(n))*self._idf.get(k,0) for k,n in vec.items() if self._idf.get(k,0)}
        size=math.sqrt(sum(v*v for v in values.values())) or 1
        return {k:v/size for k,v in values.items()}

    def _suggest_lexical(self,description):
        query=self._normalize(ngrams(description))
        if not query:return None,None,0.
        scores=[sum(v*ref.get(k,0) for k,v in query.items()) for ref in self._vectors]
        idx=max(range(len(scores)),key=lambda i:scores[i])
        return self.example_categories[idx],self.examples[idx],round(scores[idx],4)

    def _suggest_semantic(self,description):
        if self.engine=='lexical' or not self.semantic_available:return None
        if self._model is None:
            os.environ['HF_HUB_OFFLINE']='1'
            from sentence_transformers import SentenceTransformer
            self._model=SentenceTransformer(str(self.model_path.resolve()),device='cpu',local_files_only=True)
            self._reference_embeddings=self._model.encode(self.examples,normalize_embeddings=True)
        embedding=self._model.encode([description],normalize_embeddings=True)[0]
        scores=self._reference_embeddings @ embedding
        idx=int(scores.argmax())
        return self.example_categories[idx],self.examples[idx],float(scores[idx])

    @lru_cache(maxsize=200_000)
    def classify(self,description):
        desc=canonical(description)
        if desc in self.approved:
            cat,provider,status=self.approved[desc]
            if status == 'CURATED_DEMO':
                return Result(cat,provider,'curated_alias',None,False,cat!='not_a_bill' and bool(provider),
                              cat,desc,'ACCEPTED_DEMO')
        candidate,reference,score=self._suggest_lexical(desc)
        sem=self._suggest_semantic(desc)
        # Without a representative, reviewed holdout set neither cosine score NOR
        # 2-model agreement is strong enough for production auto-acceptance.
        if sem is not None and (candidate is None or sem[0]!=candidate):
            method='lexical_minilm_disagree'
        elif sem is not None:
            method='lexical_minilm_agree'
        else:
            method='lexical_suggestion'
        # ApTap's scored field MUST belong to the ten-class taxonomy.
        # This is a provisional top-1 candidate, NEVER a trusted bill label.
        candidate = candidate or (sem[0] if sem else None) or 'not_a_bill'
        return Result(candidate,None,method,score,True,False,
                      candidate,reference,'REVIEW_REQUIRED')
