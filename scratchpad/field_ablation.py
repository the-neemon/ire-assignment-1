"""BM25 document-field ablation: title vs title+abstract vs title+abstract+body.

Answers "EB-NeRD ships body text, why aren't you indexing it?" with a measurement rather
than an assumption. Results are recorded in docs/NOTES.md under "Which article fields to
index (field ablation)".

Non-destructive by design: reuses retrieval.bm25's own functions but never writes to
data/processed, so the shipped artifacts and the reported results stay untouched. Verify
with `md5sum data/processed/ebnerd_small/bm25_val.parquet` before and after.

Only EB-NeRD carries a body, so the third variant is meaningful there alone; on MIND
`document_text` drops the all-null field automatically and prints a note.

    .venv/bin/python scratchpad/field_ablation.py            # ebnerd_small val
    .venv/bin/python scratchpad/field_ablation.py mind_small
"""
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval import bootstrap, metrics                         # noqa: E402
from retrieval.bm25 import TOP_K, build_index, score_split  # noqa: E402

DATASET = sys.argv[1] if len(sys.argv) > 1 else "ebnerd_small"
# Selection would be on val in any case; test is never read here.
SPLIT = "val"
VARIANTS = {
    "title": ("title",),
    "title+abstract (ships)": ("title", "abstract"),
    "title+abstract+body": ("title", "abstract", "body"),
}

cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[DATASET]
proc = ROOT / "data/processed" / DATASET
articles = pl.read_parquet(proc / "articles.parquet")
impressions = pl.read_parquet(proc / f"impressions_{SPLIT}.parquet")

print(f"{DATASET} {SPLIT}: {impressions.height:,} impressions, {articles.height:,} articles")
body_chars = articles["body"].str.len_chars()
print(f"body: {articles['body'].null_count():,} null, "
      f"median {body_chars.median() or 0:.0f} chars, p95 {body_chars.quantile(0.95) or 0:.0f}\n")

position = {a: i for i, a in enumerate(articles["article_id"])}
published = (articles["published_time"].to_numpy()
             if articles["published_time"].null_count() < articles.height else None)

labels = [
    np.fromiter((c in set(k) for c in cand), bool, len(cand))
    for cand, k in zip(impressions["candidates"].to_list(), impressions["clicked"].to_list())
]

results = {}
for name, fields in VARIANTS.items():
    print(f"--- {name} ---")
    t0 = time.time()
    # Everything except `fields` is held fixed, so any difference is attributable to the fields.
    index, stemmer = build_index(articles, cfg, fields)
    vocab = len(index.vocab_dict)
    cand_scores, retrieved = score_split(
        index, stemmer, cfg, impressions, articles, position, published
    )
    scores = [np.asarray(s, dtype=np.float64) for s in cand_scores]
    values, keep = metrics.per_impression(scores, labels)
    recall = metrics.recall_at_k(
        pl.Series("retrieved", retrieved), impressions["clicked"], (TOP_K,), keep
    )[TOP_K]
    results[name] = {"auc": values["auc"], "ndcg10": values["ndcg@10"], "recall": recall,
                     "vocab": vocab, "secs": time.time() - t0}
    print(f"    vocab {vocab:,}   {time.time() - t0:.0f}s\n")

print(f"\n{'variant':<24} {'vocab':>8}  {'AUC':<26} {'nDCG@10':<26} {f'recall@{TOP_K}':<26}")
print("-" * 116)
for name, r in results.items():
    cells = [bootstrap.fmt(*bootstrap.ci(r[k])) for k in ("auc", "ndcg10", "recall")]
    print(f"{name:<24} {r['vocab']:>8,}  " + "  ".join(f"{c:<24}" for c in cells))

base = "title+abstract (ships)"
print(f"\npaired differences vs `{base}` (95% CI; significant if it excludes zero)")
print("-" * 116)
for name, r in results.items():
    if name == base:
        continue
    row = [name.ljust(24)]
    for key, label in (("auc", "AUC"), ("ndcg10", "nDCG@10"), ("recall", f"recall@{TOP_K}")):
        mean, lo, hi, sig = bootstrap.paired(r[key], results[base][key])
        row.append(f"{label} {mean:+.4f} [{lo:+.4f}, {hi:+.4f}] {'SIG' if sig else '   '}")
    print("  ".join(row))
