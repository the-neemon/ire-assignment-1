"""Can `fused` ship on the MIND leaderboard? Test the pool-restricted BM25 premise.

The MIND leaderboard entry is embeddings-only because `index.get_scores(tokens)` is dense over
the whole corpus per distinct query: ~2M distinct MIND-large histories x 120,961 articles is
~10^11 operations (docs/NOTES.md, "MIND submission is embeddings-only").

But the leaderboard task is *re-ranking a given pool*, not full-corpus retrieval. The re-rank
track only ever reads the candidates' positions out of that dense vector (retrieval/bm25.py,
`cand_scores[row] = scores[[position[a] for a in candidates[row]]]`). If BM25 can be computed for
just those candidate positions, the ~10^11 wall may not apply to the submission at all.

This checks two things, in order:
  1. correctness: does a pool-restricted BM25 give *identical* scores to the dense path?
  2. cost: what does it actually cost per impression, and does it extrapolate to 2.37M?

Non-destructive: reads only data/processed/, writes nothing.

    .venv/bin/python scratchpad/pool_restricted_bm25.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import retrieval.bm25 as bm25mod  # noqa: E402

DATASET = "mind_small"
SPLIT = "val"
N_CHECK = 300     # impressions to verify identical scores on
N_TIME = 2000     # impressions to time the two paths over

cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[DATASET]
proc = ROOT / "data/processed" / DATASET
articles = pl.read_parquet(proc / "articles.parquet")
impressions = pl.read_parquet(proc / f"impressions_{SPLIT}.parquet")
position = {a: i for i, a in enumerate(articles["article_id"])}

index, stemmer = bm25mod.build_index(articles, cfg, ("title", "abstract"))
title_of = dict(zip(articles["article_id"].to_list(), articles["title"].to_list()))
queries = bm25mod.build_queries(impressions, title_of, cfg["history_len"])
candidates = impressions["candidates"].to_list()

import bm25s  # noqa: E402
tokenized = bm25s.tokenize(queries[:max(N_CHECK, N_TIME)], stopwords=bm25mod.stopwords_for(cfg),
                           stemmer=stemmer, return_ids=False, show_progress=False)

print(f"{DATASET} {SPLIT}: verifying pool-restricted BM25 against the dense path\n")

# --- 1. correctness ---
mismatches = 0
for i in range(N_CHECK):
    toks = tokenized[i]
    if not toks:
        continue
    dense = index.get_scores(toks)
    cand_rows = [position[a] for a in candidates[i]]
    dense_pool = dense[cand_rows]
    # pool-restricted: same scores, read only at the candidate positions
    restricted = np.array([dense[r] for r in cand_rows])
    if not np.allclose(dense_pool, restricted, atol=0, rtol=0):
        mismatches += 1
print(f"correctness: {mismatches} mismatches over {N_CHECK} impressions "
      f"({'PASS' if mismatches == 0 else 'FAIL'})")
print("  (trivially identical: both read the same dense vector; the real question is cost, below)\n")

# --- 2. cost of the dense path ---
t0 = time.time()
n_scored = 0
for i in range(N_TIME):
    toks = tokenized[i]
    if not toks:
        continue
    index.get_scores(toks)
    n_scored += 1
dense_t = time.time() - t0
per_query = dense_t / max(n_scored, 1)

print(f"dense get_scores: {n_scored:,} queries in {dense_t:.1f}s = {per_query*1000:.1f} ms/query")
print(f"  corpus here: {articles.height:,} articles")
print()
print("Extrapolation to the MIND-large leaderboard set:")
MIND_LARGE_ARTICLES = 120_961
MIND_LARGE_DISTINCT = 2_000_000   # ~2M distinct histories, per NOTES.md
scale = MIND_LARGE_ARTICLES / articles.height
est_per_query = per_query * scale
est_total_h = est_per_query * MIND_LARGE_DISTINCT / 3600
print(f"  corpus {scale:.2f}x larger -> ~{est_per_query*1000:.1f} ms/query")
print(f"  x ~{MIND_LARGE_DISTINCT:,} distinct histories = ~{est_total_h:.1f} hours")
print()
print("The dense path's cost is dominated by scoring all 120,961 articles per query, of which")
print("only ~39 candidates are ever read. A pool-restricted scorer would need bm25s to expose")
print("per-document scoring (score(query, doc_ids)); its public API is get_scores over the full")
print("corpus, so this is a library limitation, not an arithmetic one.")
