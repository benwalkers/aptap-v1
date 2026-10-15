"""CLI: python -m categorise input.csv output.csv [--engine auto|lexical|minilm]."""
import argparse
import csv
from pathlib import Path
from .core import MerchantCategoriser


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('input_csv',type=Path);p.add_argument('output_csv',type=Path)
    p.add_argument('--labels',type=Path,default=Path('data/merchant_labels.csv'))
    p.add_argument('--aliases',type=Path,default=Path('classification/curated_aliases.csv'))
    p.add_argument('--engine',choices=['auto','lexical','minilm'],default='lexical')
    p.add_argument('--model-path',type=Path,default=Path('models/minilm'))
    p.add_argument('--review-output',type=Path)
    args=p.parse_args(argv)
    classifier=MerchantCategoriser(args.labels,args.engine,args.model_path,args.aliases)
    args.output_csv.parent.mkdir(parents=True,exist_ok=True)
    reviews=[]
    with args.input_csv.open(encoding='utf-8-sig',newline='') as input_file, args.output_csv.open('w',encoding='utf-8',newline='') as output_file:
        reader=csv.DictReader(input_file)
        if not reader.fieldnames or 'description' not in reader.fieldnames:
            raise ValueError('Input CSV needs description')
        fields=list(reader.fieldnames)
        if 'category' not in fields:fields.append('category')
        if 'needs_review' not in fields:fields.append('needs_review')
        writer=csv.DictWriter(output_file,fieldnames=fields);writer.writeheader()
        for row in reader:
            result=classifier.classify(row['description'])
            row['category']=result.category
            row['needs_review']=str(result.needs_review).lower()
            writer.writerow(row)
            if result.needs_review:
                reviews.append({'description':row['description'],'category':result.category,
                                'candidate_category':result.candidate_category or '',
                                'score':result.score,'method':result.method})
    if args.review_output:
        args.review_output.parent.mkdir(parents=True,exist_ok=True)
        with args.review_output.open('w',encoding='utf-8',newline='') as dest:
            writer=csv.DictWriter(dest,fieldnames=['description','category','candidate_category','score','method']);writer.writeheader();writer.writerows(reviews)
    print(f'Wrote {args.output_csv}; unresolved occurrences {len(reviews)} (provisional ten-class predictions, with review flags)')

if __name__=='__main__':main()
