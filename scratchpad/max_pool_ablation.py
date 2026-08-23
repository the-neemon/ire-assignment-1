"""User-vector pooling: mean vs max-similarity, on MIND (previously untested).

Shipped: user vector = mean of last history_len clicked article vectors, re-normalised; score a
candidate by cosine(user_vector, candidate_vector). That collapses a user with genuinely diverse
interests into one blurred centroid.

Alternative: score a candidate by its *best* match to any single history item,
max_h cosine(vector(h), candidate), never forming a user vector at all. Might catch "this matches
the one thing they read yesterday" even when it's unlike the rest of their history.

Non-destructive: reads only data/processed/ and the cached embedding vectors, writes nothing.

    .venv/bin/python scratchpad/max_pool_ablation.py
"""
import sys
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import retrieval.embeddings as embmod  # noqa: E402
from eval import bootstrap, metrics     # noqa: E402

DATASET = "mind_small"
SPLIT = "val"

cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[DATASET]
proc = ROOT / "data/processed" / DATASET
articles = pl.read_parquet(proc / "articles.parquet")
impressions = pl.read_parquet(proc / f"impressions_{SPLIT}.parquet")
position = {a: i for i, a in enumerate(articles["article_id"])}
history_len = cfg["history_len"]

vectors = embmod.load_vectors(DATASET, cfg, articles)

labels = [
    np.fromiter((c in set(k) for c in cand), bool, len(cand))
    for cand, k in zip(impressions["candidates"].to_list(), impressions["clicked"].to_list())
]

print(f"{DATASET} {SPLIT}: {impressions.height:,} impressions\n")

max_scores, mean_scores = [], []
for cand, hist in zip(impressions["candidates"].to_list(), impressions["history"].to_list()):
    hist_rows = [position[a] for a in hist[-history_len:] if a in position]
    cand_rows = [position[a] for a in cand]
    cand_vecs = vectors[cand_rows]  # (n_cand, dim)

    if not hist_rows:
        max_scores.append(np.zeros(len(cand)))
        mean_scores.append(np.zeros(len(cand)))
        continue

    hist_vecs = vectors[hist_rows]  # (n_hist, dim)
    sims = cand_vecs @ hist_vecs.T  # (n_cand, n_hist): every candidate x every history item
    max_scores.append(sims.max(axis=1).astype(np.float32))

    u = hist_vecs.mean(axis=0)
    u = u / (np.linalg.norm(u) + 1e-9)
    mean_scores.append((cand_vecs @ u).astype(np.float32))

v_mean, keep = metrics.per_impression(mean_scores, labels)
v_max, _ = metrics.per_impression(max_scores, labels)

print(f"mean pooling (shipped)  val AUC {bootstrap.fmt(*bootstrap.ci(v_mean['auc']))}")
print(f"max-similarity          val AUC {bootstrap.fmt(*bootstrap.ci(v_max['auc']))}")

mean_d, lo, hi, sig = bootstrap.paired(v_max["auc"], v_mean["auc"])
verdict = "beats mean pooling" if sig and mean_d > 0 else ("loses to mean pooling" if sig and mean_d < 0 else "no significant difference")
print(f"\nmax - mean: {mean_d:+.4f} [{lo:+.4f}, {hi:+.4f}]  {verdict}")
