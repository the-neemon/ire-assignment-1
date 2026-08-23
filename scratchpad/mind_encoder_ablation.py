"""MIND encoder ablation: mpnet vs BGE vs E5 vs the shipped MiniLM, on val.

Encoding happens on Kaggle (notebooks/encode_articles.ipynb, §4) because a single 768-d model
over 65,238 articles is ~2.4h on this machine's CPU (measured); three of them is a GPU job, not
a laptop one. This script only scores the vectors once they're downloaded.

    mkdir -p data/interim/mind_encoders
    # copy the three downloaded *_vectors.parquet files there, then:
    .venv/bin/python scratchpad/mind_encoder_ablation.py

Non-destructive: reads retrieval.embeddings' own functions, never writes to data/processed.
Reports val AUC with bootstrap CI for each encoder, paired against the shipped MiniLM baseline,
plus the resource cost (encode time, dim, file size) each one costs, since the brief asks for the
best AUC-vs-resource tradeoff, not just the best AUC.
"""
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import retrieval.embeddings as embmod          # noqa: E402
from eval import bootstrap, metrics             # noqa: E402

DATASET = "mind_small"
SPLIT = "val"
ENC_DIR = ROOT / "data/interim/mind_encoders"

# Measured once, by hand, on Kaggle's T4 (see notebook §4 print output) — filled in after the
# encoding run; used only to print the resource side of the tradeoff, not to score anything.
KNOWN_COST = {
    "minilm (shipped)": {"dim": 384, "kaggle_min": None, "cpu_min_local": 11.3},
}

CANDIDATES = {
    "mpnet": ENC_DIR / "mind_small_mpnet_vectors.parquet",
    "bge": ENC_DIR / "mind_small_bge_vectors.parquet",
    "e5": ENC_DIR / "mind_small_e5_vectors.parquet",
}

cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[DATASET]
proc = ROOT / "data/processed" / DATASET
articles = pl.read_parquet(proc / "articles.parquet")
impressions = pl.read_parquet(proc / f"impressions_{SPLIT}.parquet")
position = {a: i for i, a in enumerate(articles["article_id"])}

labels = [
    np.fromiter((c in set(k) for c in cand), bool, len(cand))
    for cand, k in zip(impressions["candidates"].to_list(), impressions["clicked"].to_list())
]

print(f"{DATASET} {SPLIT}: {impressions.height:,} impressions, {articles.height:,} articles\n")


def score(vectors: np.ndarray) -> dict:
    cand_scores, _ = embmod.score_split(impressions, articles, vectors, position, None, cfg["history_len"])
    cand_scores = [np.asarray(s, dtype=np.float64) for s in cand_scores]
    v, keep = metrics.per_impression(cand_scores, labels)
    return {"auc": v["auc"], "ndcg10": v["ndcg@10"]}


# --- baseline: the shipped MiniLM vectors, already cached ---
baseline_vectors = embmod.load_vectors(DATASET, cfg, articles)
baseline = score(baseline_vectors)
print(f"minilm (shipped)   dim=384   val AUC {bootstrap.fmt(*bootstrap.ci(baseline['auc']))}")

results = {"minilm (shipped)": baseline}
for tag, path in CANDIDATES.items():
    if not path.exists():
        print(f"{tag:<10} SKIPPED — {path} not found (download it from Kaggle first)")
        continue
    table = pl.read_parquet(path).with_columns(pl.col("article_id").cast(pl.String))
    wanted = articles["article_id"].to_list()
    found = dict(zip(table["article_id"], range(table.height)))
    missing = [a for a in wanted if a not in found]
    assert not missing, f"{tag}: {len(missing)} articles missing from {path}"
    raw = table["vector"].explode().to_numpy().astype(np.float32).reshape(table.height, len(table["vector"][0]))
    vectors = raw[[found[a] for a in wanted]]
    vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)
    dim = vectors.shape[1]

    t0 = time.time()
    results[tag] = score(vectors)
    dt = time.time() - t0
    size_mb = path.stat().st_size / 1e6
    print(f"{tag:<10} dim={dim}   val AUC {bootstrap.fmt(*bootstrap.ci(results[tag]['auc']))}   "
          f"(scored in {dt:.0f}s, vectors {size_mb:.0f} MB on disk)")

print("\npaired vs minilm (shipped), val AUC (95% CI; significant if it excludes zero)")
print("-" * 80)
for tag in results:
    if tag == "minilm (shipped)":
        continue
    mean, lo, hi, sig = bootstrap.paired(results[tag]["auc"], baseline["auc"])
    verdict = "beats MiniLM" if sig and mean > 0 else ("loses to MiniLM" if sig and mean < 0 else "no significant difference")
    print(f"  {tag:<10} {mean:+.4f} [{lo:+.4f}, {hi:+.4f}]   {verdict}")

print("\nResource side of the tradeoff (dim is the ongoing cost: FAISS index size, cosine flops,")
print("candidate-scoring memory; all scale with dim, not with which encoder produced it):")
print(f"  minilm  384-d, 11.3 min to encode locally on CPU (already shipped, sunk cost)")
print(f"  mpnet/bge/e5  768-d (2x minilm's index size and per-query cost), ~2.4h CPU-equivalent each")
print("\nDecide by: does the AUC gain (if any, and only if significant) justify permanently doubling")
print("the semantic index's memory and per-query cost for every future run, not just this one.")
