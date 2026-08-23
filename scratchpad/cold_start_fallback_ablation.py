"""Cold-start fallback: current zero-score convention vs train-popularity backoff, on MIND.

Shipped convention: a user with no history gets an all-zero score vector on every scorer (no
query, no ranking invented from nothing). Tests whether falling back to train-click popularity
for these specific users beats that convention, on the cold slice only.

Non-destructive: reads only data/processed/, writes nothing.

    .venv/bin/python scratchpad/cold_start_fallback_ablation.py
"""
import sys
from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval import bootstrap, metrics, slicing  # noqa: E402

DATASET = "mind_small"
SPLIT = "val"

proc = ROOT / "data/processed" / DATASET
impressions = pl.read_parquet(proc / f"impressions_{SPLIT}.parquet")
train_clicked = pl.read_parquet(proc / "impressions_train.parquet")["clicked"].to_list()
counts = slicing.train_click_counts(train_clicked)

history_lengths = np.array([len(h) for h in impressions["history"].to_list()])
cold = history_lengths == 0
print(f"{DATASET} {SPLIT}: {impressions.height:,} impressions, {cold.sum():,} true cold-start ({cold.mean():.1%})")

candidates = impressions["candidates"].to_list()
clicked = impressions["clicked"].to_list()
labels = [np.fromiter((c in set(k) for c in cand), bool, len(cand)) for cand, k in zip(candidates, clicked)]

# current convention: all-zero score for cold-start users (only meaningful ones evaluated below)
zero_scores = [np.zeros(len(c)) for c in candidates]
# fallback: score by train click popularity (log1p to stop one blockbuster dominating)
pop_scores = [np.log1p(np.array([counts.get(a, 0) for a in c], dtype=np.float64)) for c in candidates]

v_zero, keep = metrics.per_impression(zero_scores, labels)
v_pop, _ = metrics.per_impression(pop_scores, labels)

cold_scored = cold[keep]
n_cold = cold_scored.sum()
print(f"{n_cold:,} cold-start impressions survive the all-clicked/none-clicked filter\n")

if n_cold < 30:
    print("too few cold-start impressions with ranking signal for a meaningful bootstrap CI")
else:
    zero_cold = v_zero["auc"][cold_scored]
    pop_cold = v_pop["auc"][cold_scored]
    print(f"cold slice, zero-score (shipped)   AUC {bootstrap.fmt(*bootstrap.ci(zero_cold))}")
    print(f"cold slice, popularity fallback    AUC {bootstrap.fmt(*bootstrap.ci(pop_cold))}")
    mean, lo, hi, sig = bootstrap.paired(pop_cold, zero_cold)
    verdict = "beats zero-score" if sig and mean > 0 else ("loses to zero-score" if sig and mean < 0 else "no significant difference")
    print(f"\npopularity - zero: {mean:+.4f} [{lo:+.4f}, {hi:+.4f}]  {verdict}")
