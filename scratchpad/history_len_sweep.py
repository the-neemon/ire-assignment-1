"""history_len sweep on MIND, both scorers.

The original sweep (docs/NOTES.md, "BM25 results") only ran on EB-NeRD val, where it came back
flat because EB-NeRD's median history is 258 clicks and cutting at 30 barely touches the query.
MIND's median history is 20 (mean 33.3), so a cutoff of 30 was close to "use everything" there,
and the shipped value was never actually checked against MIND's own history distribution. This
found a plateau at 100 (bm25 +0.0039, emb +0.0018 AUC over 30, both significant, 100/200/300/558
indistinguishable), which is now `mind_small`'s `history_len` in configs/datasets.yaml.

Non-destructive: passes history_len as a plain argument to each call rather than mutating any
module state, and never writes to data/processed. Verify with
`md5sum data/processed/mind_small/{bm25,emb}_val.parquet` before and after.

    .venv/bin/python scratchpad/history_len_sweep.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import retrieval.bm25 as bm25mod                    # noqa: E402
import retrieval.embeddings as embmod                # noqa: E402
from eval import bootstrap, metrics                  # noqa: E402

DATASET = "mind_small"
SPLIT = "val"
SWEEP = [30, 100]   # just the shipped-vs-old comparison, to confirm the refactor   # 558 = MIND-small's max history length
SHIPPED = 100   # what configs/datasets.yaml ships for mind_small, post-sweep

cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[DATASET]
proc = ROOT / "data/processed" / DATASET
articles = pl.read_parquet(proc / "articles.parquet")
impressions = pl.read_parquet(proc / f"impressions_{SPLIT}.parquet")

print(f"{DATASET} {SPLIT}: {impressions.height:,} impressions, {articles.height:,} articles")
hist_len = impressions["history"].list.len()
print(f"history length: median {hist_len.median():.0f}, mean {hist_len.mean():.1f}, "
      f"max {hist_len.max()}\n")

position = {a: i for i, a in enumerate(articles["article_id"])}
published = None  # MIND carries no publication dates

labels = [
    np.fromiter((c in set(k) for c in cand), bool, len(cand))
    for cand, k in zip(impressions["candidates"].to_list(), impressions["clicked"].to_list())
]

# --- BM25: index is independent of HISTORY_LEN, build once ---
index, stemmer = bm25mod.build_index(articles, cfg, ("title", "abstract"))

# --- embeddings: vectors are independent of HISTORY_LEN, load once (cached) ---
vectors = embmod.load_vectors(DATASET, cfg, articles)
print()

title_of = dict(zip(articles["article_id"], articles["title"]))

results = {"bm25": {}, "emb": {}}
for n in SWEEP:
    t0 = time.time()
    bm25_queries = bm25mod.build_queries(impressions, title_of, n)
    # score_split rebuilds the query list itself from cfg["history_len"], so swap that in
    # for the duration of this call rather than re-deriving score_split's internals here.
    cfg_n = {**cfg, "history_len": n}
    bm25_scores, _ = bm25mod.score_split(index, stemmer, cfg_n, impressions, articles, position, published)
    bm25_scores = [np.asarray(s, dtype=np.float64) for s in bm25_scores]
    v, keep = metrics.per_impression(bm25_scores, labels)
    results["bm25"][n] = {"auc": v["auc"], "ndcg10": v["ndcg@10"]}

    emb_scores, _ = embmod.score_split(impressions, articles, vectors, position, published, n)
    emb_scores = [np.asarray(s, dtype=np.float64) for s in emb_scores]
    v, keep = metrics.per_impression(emb_scores, labels)
    results["emb"][n] = {"auc": v["auc"], "ndcg10": v["ndcg@10"]}

    print(f"  history_len={n:<4} done in {time.time()-t0:.0f}s")

print(f"\n{'history_len':<12} {'bm25 AUC':<26} {'emb AUC':<26} {'bm25 nDCG@10':<26} {'emb nDCG@10':<26}")
print("-" * 116)
for n in SWEEP:
    row = [str(n) + ("  (shipped)" if n == SHIPPED else "")]
    for scorer in ("bm25", "emb"):
        row.append(bootstrap.fmt(*bootstrap.ci(results[scorer][n]["auc"])))
    for scorer in ("bm25", "emb"):
        row.append(bootstrap.fmt(*bootstrap.ci(results[scorer][n]["ndcg10"])))
    print(f"{row[0]:<12} {row[1]:<26} {row[2]:<26} {row[3]:<26} {row[4]:<26}")

print(f"\npaired differences vs history_len={SHIPPED} (95% CI; significant if it excludes zero)")
print("-" * 116)
for scorer in ("bm25", "emb"):
    for n in SWEEP:
        if n == SHIPPED:
            continue
        mean, lo, hi, sig = bootstrap.paired(results[scorer][n]["auc"], results[scorer][SHIPPED]["auc"])
        print(f"  {scorer:<6} n={n:<4} AUC {mean:+.4f} [{lo:+.4f}, {hi:+.4f}]  {'SIG' if sig else '   '}")
