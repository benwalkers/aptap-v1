"""Portable, print-ready one-page commercial report. Descriptive, not causal."""
from __future__ import annotations

import html
import random
import statistics
from collections import defaultdict
from pathlib import Path


def bootstrap_interval(values, seed=2026, repeats=1000):
    if len(values) < 5:
        return None
    rng = random.Random(seed)
    estimates = [statistics.mean(rng.choices(values, k=len(values))) for _ in range(repeats)]
    estimates.sort()
    return estimates[int(.025 * repeats)], estimates[int(.975 * repeats)]


def _money(value):
    return f"{'+' if value >= 0 else '−'}£{abs(value):.2f}"


def _svg_chart(summaries):
    """Genuine SVG bar chart: percentage of candidates with lower new payments."""
    left, right, step, top = 122, 490, 46, 29
    height = top + len(summaries) * step + 43
    elements = [f'<svg class="category-chart" viewBox="0 0 640 {height}" role="img" '
                'aria-label="Share of candidate changes with lower observed new payments, by category">',
                '<text x="122" y="17" class="axis-label">0%</text>',
                '<text x="306" y="17" class="axis-label">50%</text>',
                '<text x="490" y="17" class="axis-label">100%</text>',
                f'<line x1="122" x2="122" y1="25" y2="{height - 24}" class="axis"/>',
                f'<line x1="306" x2="306" y1="25" y2="{height - 24}" class="axis dash"/>',
                f'<line x1="490" x2="490" y1="25" y2="{height - 24}" class="axis"/>']
    for i, r in enumerate(summaries):
        y = top + i * step
        width = right * r['lower_share'] / 100 - left * r['lower_share'] / 100
        label = html.escape(r['category'].replace('_', ' ').title())
        fill = '#118a81' if r['lower_share'] >= 50 else '#da8560'
        elements.extend([
            f'<text x="5" y="{y + 22}" class="category-label">{label}</text>',
            f'<rect x="{left}" y="{y + 4}" width="{right-left}" height="23" rx="4" fill="#eaf0f5"/>',
            f'<rect x="{left}" y="{y + 4}" width="{width:.2f}" height="23" rx="4" fill="{fill}"/>',
            f'<text x="{right + 9}" y="{y + 22}" class="pct-label">{r["lower_share"]:.1f}%</text>',
        ])
    elements.append('</svg>')
    return ''.join(elements)


def make_report(comparisons, destination: Path, data_cutoff, metrics, evidence_validation=None):
    """Preserves the previous tuple summary return contract for pipeline.run_metrics."""
    groups = defaultdict(list)
    for item in comparisons:
        groups[item['category']].append(item)
    summaries = []
    chart_rows = []
    table_rows = []
    for category, items in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        changes = [float(x['saving']) for x in items]
        ci = bootstrap_interval(changes)
        mean = statistics.mean(changes)
        median = statistics.median(changes)
        lower = sum(x > 0 for x in changes)
        share = 100 * lower / len(changes)
        provisional = sum(x['evidence'] == 'provisional' for x in items)
        summaries.append((category, len(items), mean, ci, provisional))
        chart_rows.append({'category':category, 'lower_share':share})
        ci_text = f'{_money(ci[0])} to {_money(ci[1])}' if ci else 'Insufficient sample'
        table_rows.append('<tr>'
            f'<td>{html.escape(category.replace("_", " ").title())}</td>'
            f'<td>{len(items)}</td><td>{lower}/{len(items)} ({share:.1f}%)</td>'
            f'<td class="num">{_money(median)}</td><td class="num">{_money(mean)}</td>'
            f'<td>{html.escape(ci_text)}</td></tr>')
    total = len(comparisons)
    lower_total = sum(float(row['saving']) > 0 for row in comparisons)
    share_total = 100 * lower_total / total if total else 0
    unique_customers = len({row['customer_id'] for row in comparisons})
    overall_median = statistics.median([float(row['saving']) for row in comparisons]) if total else 0
    evidence_counts = (evidence_validation or {}).get('evidence_counts', {})
    provisional = evidence_counts.get('PROVISIONAL', sum(r[4] for r in summaries))
    repeated = evidence_counts.get('REPEATED_NEW_PROVIDER', 0)
    supported = evidence_counts.get('SUPPORTED_PAYMENT_PATTERN', 0)
    verified = (evidence_validation or {}).get('externally_confirmed_switches', 0)
    chart = _svg_chart(chart_rows) if chart_rows else '<p>No eligible comparisons.</p>'
    row_html = ''.join(table_rows) or '<tr><td colspan="6">No observed provider-change comparisons</td></tr>'
    document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ApTap | Commercial opportunity and evidence</title>
<style>
@page{{size:A4 landscape;margin:11mm}}
*{{box-sizing:border-box}}body{{max-width:1150px;margin:24px auto;padding:0 17px;font-family:Inter,Arial,Helvetica,sans-serif;color:#18304c;background:#f7f9fc;font-size:12px;line-height:1.45}}
main{{background:#fff;border:1px solid #e2e8f1;padding:24px 29px;border-radius:16px;box-shadow:0 10px 35px #17324c0d}}
.eyebrow{{font-size:10px;font-weight:800;letter-spacing:2px;color:#097b8e}}h1{{font-size:27px;line-height:1.12;margin:5px 0 6px}}h2{{font-size:15px;margin:13px 0 7px}}.muted,.fine{{color:#596d81}}.fine{{font-size:10px;line-height:1.35}}.verdict{{background:#e8f6f3;border-left:5px solid #0d897d;border-radius:8px;padding:10px 13px;margin:13px 0}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}}.stat{{background:#eef3f8;border-radius:9px;padding:10px}}.stat .value{{font-size:21px;font-weight:800}}.stat .label{{font-size:10px;color:#5b6e82}}.columns{{display:grid;grid-template-columns:1fr 1.1fr;gap:23px;align-items:start}}.category-chart{{width:100%;max-height:220px}}
.axis{{stroke:#b5c4d2;stroke-width:1}}.dash{{stroke-dasharray:3 5}}.category-label,.pct-label{{font-size:14px;fill:#26425d;font-weight:600}}.axis-label{{font-size:12px;fill:#64748b}}table{{width:100%;border-collapse:collapse;font-size:10.5px}}td,th{{border-bottom:1px solid #dde7ef;text-align:left;padding:6px 7px}}th{{color:#fff;background:#244660}}td.num{{white-space:nowrap}}.notes{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.notes p{{margin:4px 0}}.pill{{color:#96520b;background:#fff0d6;border-radius:4px;padding:2px 6px;font-size:10px}}
@media print{{body{{padding:0;margin:0;background:white}}main{{border:none;box-shadow:none;padding:0;border-radius:0}}h1{{font-size:24px}}.stats{{gap:5px}}.stat{{padding:7px}}h2{{margin-top:10px}}.notes{{gap:10px}}}}
</style></head><body><main>
<div class="eyebrow">APTAP · COMMERCIAL OPPORTUNITY & EVIDENCE · SYNTHETIC SAMPLE</div>
<h1>Do customers pay less after an apparent provider change?</h1>
<div class="muted">Cut-off: {html.escape(str(data_cutoff))} · Observed old minus new payment amounts; positive means the new payment was lower.</div>
<div class="verdict"><strong>Finding:</strong> {'Lower observed new payments appear in some candidate changes.' if total else 'No provider-change candidates met current evidence criteria.'} <strong>These are not confirmed switches or proven savings.</strong> Validate product, consumption and cancellation before customer-facing claims.</div>
<div class="stats">
<div class="stat"><div class="value">{total:,}</div><div class="label">Candidate comparisons · {unique_customers:,} customers</div></div>
<div class="stat"><div class="value">{share_total:.1f}%</div><div class="label">Lower new payments · {lower_total:,}/{total:,}</div></div>
<div class="stat"><div class="value">{_money(overall_median)}</div><div class="label">Median observed difference per comparison</div></div>
<div class="stat"><div class="value">{supported:,}</div>Supported payment patterns</div>
<div class="stat"><div class="value">{verified:,}</div>Externally confirmed</div>
</div>
<div class="columns"><section><h2>Share with a lower observed new payment</h2>{chart}<div class="fine">Comparison selection is non-random. This chart shows descriptive proportions, not probabilities of switching or causal savings.</div></section>
<section><h2>Category evidence and uncertainty</h2><table><thead><tr><th>Category</th><th>n</th><th>Lower new</th><th>Median £</th><th>Mean £</th><th>95% CI for mean*</th></tr></thead><tbody>{row_html}</tbody></table></section></div>
<div class="notes"><section><h2>Commercial recommendation</h2><p><strong>Energy:</strong> prioritise verification of apparent lower bills. <strong>Mobile:</strong> investigate variable results before marketing. <strong>Broadband:</strong> defer claims—sample is too small. Test against verified tariffs, consumption, promotions and longer histories.</p></section>
<section><h2>Evidence quality <span class="pill">Candidate data only</span></h2><p>{provisional:,} provisional; {repeated:,} with repeated new-provider months; {supported:,} with observed repeated payments on both sides. None demonstrates account cancellation or customer savings caused by switching. Three months cannot establish long-term outcomes.</p></section></div>
<p class="fine">*1,000-resample nonparametric bootstrap of selected candidate-level differences when n≥5; selection bias, possible repeated customers and product/usage confounding are not addressed. Source reconciliation: {metrics['raw']:,} raw = {metrics['clean']:,} active clean + {metrics['rejected']:,} rejected/superseded. Evidence: outputs/switch_evidence.csv and outputs/switch_validation_summary.json. Not a financial-loss, offer-conversion or ApTap-attribution estimate.</p>
</main></body></html>'''
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding='utf-8')
    return summaries
