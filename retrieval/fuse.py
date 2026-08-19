"""Combine the lexical and semantic scores into one ranking.

BM25 scores and cosine similarities live on different scales, and BM25's scale varies with
query length, so a global normalisation would not make them comparable. Both are
z-normalised *within each candidate pool* instead, which is the only place the comparison
has to hold, then mixed:

    score = alpha * emb_z + (1 - alpha) * bm25_z

alpha is chosen on **val** and applied unchanged to test. Choosing it on test would tune a
hyper-parameter on the reported number and quietly invalidate it — the same temporal
hygiene the split enforces for features.

    python -m retrieval.fuse
    python -m retrieval.fuse ebnerd_demo

Writes, per dataset and split:
    fused_<split>.parquet   impression_id, fused   aligned to `candidates`
Records the chosen alpha in fusion_alpha.json.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"

ALPHAS = np.round(np.arange(0.0, 1.01, 0.05), 2)


def load_split(name: str, split: str) -> pl.DataFrame:
    base = PROC / name
    return (
        pl.read_parquet(base / f"impressions_{split}.parquet")
        .join(pl.read_parquet(base / f"bm25_{split}.parquet"), on="impression_id")
        .join(pl.read_parquet(base / f"emb_{split}.parquet"), on="impression_id")
    )


def zscore(values: np.ndarray) -> np.ndarray:
    """Standardise within one pool. A pool with no spread carries no information."""
    # Within-pool, not global: BM25 scores scale with query length, so a user with a long
    # history gets bigger numbers everywhere. Ranking only ever happens inside one pool, so
    # that is the only scope where the two scorers need to be comparable.
    spread = values.std()
    if spread < 1e-12:
        # Every candidate scored the same (typically a cold-start pool of zeros). Returning
        # zeros keeps the ranking neutral; dividing by ~0 would manufacture noise as signal.
        return np.zeros_like(values)
    return (values - values.mean()) / spread


def prepare(df: pl.DataFrame):
    """Per-impression (bm25_z, emb_z, labels). Labels are None where AUC is undefined."""
    rows = []
    for cand, clicked, bm25, emb in zip(
        df["candidates"].to_list(), df["clicked"].to_list(),
        df["bm25"].to_list(), df["emb"].to_list(),
    ):
        b = zscore(np.asarray(bm25, dtype=np.float64))
        e = zscore(np.asarray(emb, dtype=np.float64))
        y = np.fromiter((c in set(clicked) for c in cand), dtype=bool, count=len(cand))
        # None marks a pool where AUC is undefined (all or nothing clicked). I keep the row
        # so scores stay aligned with the impression order, and skip it when averaging.
        rows.append((b, e, None if (y.all() or not y.any()) else y))
    return rows


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    order = np.argsort(-scores)
    ranks = np.empty(len(scores))
    ranks[order] = np.arange(1, len(scores) + 1)
    return float((ranks[~labels][None, :] > ranks[labels][:, None]).mean())


def mean_auc(rows, alpha: float) -> float:
    scores = [
        auc(alpha * e + (1 - alpha) * b, y) for b, e, y in rows if y is not None
    ]
    return float(np.mean(scores))


def run(name: str, splits: list[str]) -> None:
    print(f"\n{name}")
    # Sweep alpha on val only. One scalar over 21 grid points is a small enough search that
    # a grid beats anything cleverer, and val is the only split I am allowed to tune on:
    # picking alpha on test would mean reporting a number I had already optimised against.
    val = prepare(load_split(name, "val"))
    curve = {a: mean_auc(val, a) for a in ALPHAS}
    alpha = max(curve, key=curve.get)
    print(f"  alpha tuned on val: {alpha:.2f}  (val AUC {curve[alpha]:.4f})")
    print(f"    bm25 only  alpha=0.00 -> {curve[0.0]:.4f}")
    print(f"    emb only   alpha=1.00 -> {curve[1.0]:.4f}")

    (PROC / name / "fusion_alpha.json").write_text(
        json.dumps({"alpha": float(alpha), "tuned_on": "val",
                    "val_auc_by_alpha": {str(k): v for k, v in curve.items()}}, indent=2)
    )

    for split in splits:
        df = load_split(name, split)
        rows = prepare(df)
        fused = [(alpha * e + (1 - alpha) * b).astype(np.float32) for b, e, _ in rows]
        pl.DataFrame({
            "impression_id": df["impression_id"],
            "fused": [f.tolist() for f in fused],
        }).write_parquet(PROC / name / f"fused_{split}.parquet")
        print(f"  {split:<5} AUC={mean_auc(rows, alpha):.4f}  ({df.height:,} impressions)")


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="*", default=list(config))
    parser.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    args = parser.parse_args()

    for name in args.datasets:
        run(name, args.splits)


if __name__ == "__main__":
    main()
