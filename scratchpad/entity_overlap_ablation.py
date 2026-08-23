"""Entity overlap as a candidate signal, on MIND (previously untested, unscored).

MIND ships clean Wikidata-linked entities, currently parsed into the feature store and never
scored (docs/NOTES.md: "nothing scores on entities yet"). Tests two things: does entity overlap
alone carry ranking signal, and does blending it into the shipped `fused` score help.

Score = Jaccard(candidate's entities, union of the user's last history_len articles' entities).
Impressions where the user's entity set is empty score 0 for every candidate (no signal to give),
same convention as a cold-start user's zero embedding score.

Non-destructive: reads only data/processed/, writes nothing.

    .venv/bin/python scratchpad/entity_overlap_ablation.py
"""
import sys
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval import bootstrap, metrics  # noqa: E402

DATASET = "mind_small"
SPLIT = "val"
ALPHAS = np.round(np.arange(0.0, 0.51, 0.05), 2)  # entity signal is sparse; don't expect it to dominate

cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[DATASET]
proc = ROOT / "data/processed" / DATASET
articles = pl.read_parquet(proc / "articles.parquet")
impressions = pl.read_parquet(proc / f"impressions_{SPLIT}.parquet")
fused = pl.read_parquet(proc / f"fused_{SPLIT}.parquet")

entities_of = dict(zip(articles["article_id"].to_list(), articles["entities"].to_list()))
history_len = cfg["history_len"]

labels = [
    np.fromiter((c in set(k) for c in cand), bool, len(cand))
    for cand, k in zip(impressions["candidates"].to_list(), impressions["clicked"].to_list())
]


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def zscore(values: np.ndarray) -> np.ndarray:
    spread = values.std()
    return np.zeros_like(values) if spread < 1e-12 else (values - values.mean()) / spread


print(f"{DATASET} {SPLIT}: {impressions.height:,} impressions")
print(f"entity coverage: {sum(1 for e in entities_of.values() if e):,}/{len(entities_of):,} articles\n")

entity_scores, fused_scores = [], []
for row, (cand, hist) in enumerate(zip(impressions["candidates"].to_list(), impressions["history"].to_list())):
    user_entities: set = set()
    for a in hist[-history_len:]:
        user_entities.update(entities_of.get(a, []))
    e = np.array([jaccard(set(entities_of.get(a, [])), user_entities) for a in cand], dtype=np.float64)
    entity_scores.append(e)

fused_scores = [np.asarray(f, dtype=np.float64) for f in fused["fused"].to_list()]

# --- standalone: does entity overlap alone carry ranking signal? ---
v, keep = metrics.per_impression(entity_scores, labels)
print(f"entity overlap alone   val AUC {bootstrap.fmt(*bootstrap.ci(v['auc']))}")
nonzero = sum(1 for e in entity_scores if e.any())
print(f"  ({nonzero:,}/{len(entity_scores):,} impressions had a nonzero entity score)\n")

# --- coarse fusion sweep: entity + fused ---
ez = [zscore(e) for e in entity_scores]
fz = [zscore(f) for f in fused_scores]
ys = [np.fromiter((c in set(k) for c in cand), bool, len(cand))
      for cand, k in zip(impressions["candidates"].to_list(), impressions["clicked"].to_list())]
keep_mask = np.array([y.any() and not y.all() for y in ys])


def mean_auc(alpha):
    aucs = []
    for e, f, y, ok in zip(ez, fz, ys, keep_mask):
        if not ok:
            continue
        s = alpha * e + (1 - alpha) * f
        order = np.argsort(-s, kind="stable")
        ranks = np.empty(len(s)); ranks[order] = np.arange(1, len(s) + 1)
        aucs.append((ranks[~y][None, :] > ranks[y][:, None]).mean())
    return np.mean(aucs)


curve = {a: mean_auc(a) for a in ALPHAS}
best = max(curve, key=curve.get)
print("entity+fused sweep (val AUC):")
for a in ALPHAS:
    marker = "  <- best" if a == best else ""
    print(f"  alpha={a:.2f}  {curve[a]:.4f}{marker}")

if best > 0:
    per_imp_at_best = []
    for e, f, y, ok in zip(ez, fz, ys, keep_mask):
        if not ok:
            continue
        s = best * e + (1 - best) * f
        order = np.argsort(-s, kind="stable")
        ranks = np.empty(len(s)); ranks[order] = np.arange(1, len(s) + 1)
        per_imp_at_best.append((ranks[~y][None, :] > ranks[y][:, None]).mean())
    per_imp_at_best = np.array(per_imp_at_best)
    fused_auc = v_fused = metrics.per_impression(fused_scores, labels)[0]["auc"]
    mean, lo, hi, sig = bootstrap.paired(per_imp_at_best, fused_auc)
    print(f"\nbest blend vs fused alone: {mean:+.4f} [{lo:+.4f}, {hi:+.4f}]  "
          f"{'significant' if sig else 'not significant'}")
else:
    print("\nbest alpha is 0.0: the sweep found no blend of entities that beats fused alone.")
