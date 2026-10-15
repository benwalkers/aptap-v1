"""Exploratory one-vs-rest PR evaluation of ApTap lexical and optional MiniLM retrieval.

Run from project root:
  python scripts/benchmark_pr_curves.py
  HF_HUB_OFFLINE=1 python scripts/benchmark_pr_curves.py --with-minilm

No supervised model is fitted. Scores come from leave-one-DESCRIPTION-out
reference retrieval, NOT a merchant-family-held-out evaluation. Treat results
as exploratory: labels are tiny, imbalanced, and partly uncertain.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "scripts"))

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)

from categorise.core import CATEGORIES, CORRECTIONS, canonical
from benchmark_classifiers import lexical


def read_labels(path: Path) -> list[tuple[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        examples = [
            (canonical(r["description"]),
             CORRECTIONS.get(canonical(r["description"]), r["category"].strip()))
            for r in csv.DictReader(stream)
        ]
    if not examples:
        raise ValueError("No labelled descriptions")
    if len(set(x for x, _ in examples)) != len(examples):
        raise ValueError("Repeated canonical descriptors; review before evaluation")
    invalid = set(c for _, c in examples) - set(CATEGORIES)
    if invalid:
        raise ValueError(f"Invalid categories: {sorted(invalid)}")
    return examples


def minilm_scores(rows: list[tuple[str, str]], model_path: Path):
    os.environ["HF_HUB_OFFLINE"] = "1"
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(model_path.resolve()), local_files_only=True, device="cpu")
    embeddings = model.encode([d for d, _ in rows], normalize_embeddings=True)
    classes = sorted(CATEGORIES)
    results = []
    for i in range(len(rows)):
        row_scores = {c: -1.0 for c in classes}
        for j, (_, cls) in enumerate(rows):
            if i != j:
                row_scores[cls] = max(row_scores[cls], float(embeddings[i] @ embeddings[j]))
        results.append(row_scores)
    return results


def evaluate(name: str, rows, score_rows, out: Path, min_support_plot: int):
    # Same forced top-one rule as the original benchmark (no UNKNOWN/abstention).
    y_true = np.asarray([c for _, c in rows])
    classes = sorted(CATEGORIES)
    y_pred = np.asarray([max(s, key=s.get) for s in score_rows])
    per_category = []
    plotted = []

    for category in classes:
        binary = y_true == category
        support = int(binary.sum())
        score = np.asarray([float(row[category]) for row in score_rows])
        if support == 0 or support == len(rows):
            continue
        p, r, thresholds = precision_recall_curve(binary, score)
        ap = float(average_precision_score(binary, score))
        prec = float(precision_score(binary, y_pred == category, zero_division=0))
        rec = float(recall_score(binary, y_pred == category, zero_division=0))
        f1 = float(f1_score(binary, y_pred == category, zero_division=0))
        per_category.append({
            "model": name,
            "category": category,
            "support": support,
            "prevalence": round(support / len(rows), 5),
            "average_precision": round(ap, 5),
            "top1_precision": round(prec, 5),
            "top1_recall": round(rec, 5),
            "top1_f1": round(f1, 5),
            "evidence_note": "VERY_LOW_SUPPORT" if support < 5 else "EXPLORATORY",
        })
        if support >= min_support_plot:
            plotted.append((category, support, ap, r, p))

    # Plot only reasonably represented categories; even these are not
    # sufficiently large to support reliable production threshold selection.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 6))
    for category, support, ap, recall, precision in plotted:
        ax.step(recall, precision, where="post", label=f"{category} (n={support}, AP={ap:.2f})")
    ax.set(xlim=(0, 1.02), ylim=(0, 1.02), xlabel="Recall", ylabel="Precision",
           title=f"ApTap exploratory PR curves — {name} (leave-one-description-out)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize="small", loc="lower left")
    fig.tight_layout()
    fig.savefig(out / f"pr_curves_{name}.png", dpi=170)
    plt.close(fig)

    return {
        "model": name,
        "n_descriptors": len(rows),
        "top1_accuracy": round(float((y_pred == y_true).mean()), 5),
        "top1_macro_f1": round(float(f1_score(y_true, y_pred, labels=classes, average="macro", zero_division=0)), 5),
        "macro_average_precision": round(float(np.mean([v["average_precision"] for v in per_category])), 5),
        "low_support_classes": [v["category"] for v in per_category if v["support"] < 5],
        "per_category": per_category,
        "plot": f"pr_curves_{name}.png",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=PROJECT / "data/merchant_labels.csv")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "outputs/pr_evaluation")
    parser.add_argument("--with-minilm", action="store_true")
    parser.add_argument("--model-path", type=Path, default=PROJECT / "models/minilm")
    parser.add_argument("--min-support-plot", type=int, default=5)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_labels(args.labels)
    scores = {"char_tfidf": lexical(rows)}
    if args.with_minilm:
        scores["minilm"] = minilm_scores(rows, args.model_path)

    results = [
        evaluate(name, rows, model_scores, args.output_dir, args.min_support_plot)
        for name, model_scores in scores.items()
    ]

    report = {
        "design": "Exploratory leave-one-description-out, reference retrieval (NO supervised fit)",
        "caveats": [
            "NOT an independent held-out test set or merchant-family-held-out validation.",
            "Supplied labels may contain unresolved errors; only two known corrections applied.",
            "PR / AP use one-vs-rest similarity rankings, NOT calibrated class probabilities.",
            "Top-1 precision/recall/F1 FORCE a category; deployed funnel may abstain UNKNOWN.",
            "Support is too small for robust thresholds, confidence intervals or production claims.",
        ],
        "models": results,
    }
    (args.output_dir / "pr_evaluation_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output_dir / "pr_by_category.csv").open("w", newline="", encoding="utf-8") as stream:
        flattened = [row for result in results for row in result["per_category"]]
        writer = csv.DictWriter(stream, fieldnames=list(flattened[0]))
        writer.writeheader()
        writer.writerows(flattened)

    for m in results:
        print(f"{m['model']}: top1_accuracy={m['top1_accuracy']:.3f}, "
              f"macro_F1={m['top1_macro_f1']:.3f}, macro_AP={m['macro_average_precision']:.3f}")
    print(f"Outputs: {args.output_dir}")


if __name__ == "__main__":
    main()
