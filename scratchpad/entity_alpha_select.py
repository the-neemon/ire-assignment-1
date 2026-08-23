"""Select the entity blend alpha on val, then report it on test. Never select on test.

Val picks alpha; test is reported once with that fixed alpha, exactly the discipline used for the
fusion weight and every encoder choice in this project.

    .venv/bin/python scratchpad/entity_alpha_select.py
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
ALPHAS = np.round(np.arange(0.0, 0.51, 0.05), 2)

cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[DATASET]
proc = ROOT / "data/processed" / DATASET
articles = pl.read_parquet(proc / "articles.parquet")
entities_of = dict(zip(articles["article_id"].to_list(), articles["entities"].to_list()))
history_len = cfg["history_len"]


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def zscore(v: np.ndarray) -> np.ndarray:
    s = v.std()
    return np.zeros_like(v) if s < 1e-12 else (v - v.mean()) / s


def load(split):
    imp = pl.read_parquet(proc / f"impressions_{split}.parquet")
    emb = pl.read_parquet(proc / f"emb_{split}.parquet")
    cands = imp["candidates"].to_list()
    hists = imp["history"].to_list()
    clicked = imp["clicked"].to_list()
    ys = [np.fromiter((c in set(k) for c in cand), bool, len(cand)) for cand, k in zip(cands, clicked)]
    ez, fz = [], []
    for cand, hist in zip(cands, hists):
        ue: set = set()
        for a in hist[-history_len:]:
            ue.update(entities_of.get(a, []))
        ez.append(zscore(np.array([jaccard(set(entities_of.get(a, [])), ue) for a in cand], dtype=np.float64)))
    fz = [zscore(np.asarray(e, dtype=np.float64)) for e in emb["emb"].to_list()]
    keep = np.array([y.any() and not y.all() for y in ys])
    return ez, fz, ys, keep


def per_impression_auc(ez, fz, ys, keep, alpha):
    out = []
    for e, f, y, ok in zip(ez, fz, ys, keep):
        if not ok:
            continue
        s = alpha * e + (1 - alpha) * f
        order = np.argsort(-s, kind="stable")
        r = np.empty(len(s)); r[order] = np.arange(1, len(s) + 1)
        out.append((r[~y][None, :] > r[y][:, None]).mean())
    return np.array(out)


print(f"{DATASET}: selecting entity blend alpha on val, reporting on test\n")

vez, vfz, vys, vkeep = load("val")
curve = {a: per_impression_auc(vez, vfz, vys, vkeep, a).mean() for a in ALPHAS}
best = max(curve, key=curve.get)
print("val sweep:")
for a in ALPHAS:
    print(f"  alpha={a:.2f}  {curve[a]:.4f}" + ("   <- selected" if a == best else ""))

print(f"\nselected alpha = {best:.2f} on val, now applied unchanged to test\n")

tez, tfz, tys, tkeep = load("test")
base_test = per_impression_auc(tez, tfz, tys, tkeep, 0.0)
blend_test = per_impression_auc(tez, tfz, tys, tkeep, best)

print(f"test, emb alone        AUC {bootstrap.fmt(*bootstrap.ci(base_test))}")
print(f"test, emb+entity a={best:.2f}  AUC {bootstrap.fmt(*bootstrap.ci(blend_test))}")
mean, lo, hi, sig = bootstrap.paired(blend_test, base_test)
print(f"\ntest, blend - emb: {mean:+.4f} [{lo:+.4f}, {hi:+.4f}]  "
      f"{'SIGNIFICANT' if sig else 'NOT significant'}")
