"""Ranking metrics, computed per impression so the harness can slice and bootstrap them.

Every function takes the scores for one impression's candidate pool and a boolean label
array, and returns one number. Aggregation, slicing and confidence intervals all happen on
the resulting per-impression vector — that is what makes bootstrapping possible at all.

Impressions where every candidate is clicked, or none is, carry no ranking information;
`per_impression` skips them and reports how many it dropped.
"""

import numpy as np
import polars as pl


def ranks_of(scores: np.ndarray) -> np.ndarray:
    """1-based rank of each candidate, best first. Ties broken by position, deterministic."""
    # argsort gives me "which candidate sits at each rank"; I need the inverse, "what rank
    # does each candidate hold", so I scatter positions back through `order` rather than
    # sorting twice. `kind="stable"` is what makes ties fall back to original order, so the
    # same input always produces the same ranking.
    order = np.argsort(-scores, kind="stable")
    ranks = np.empty(len(scores), dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1)
    return ranks


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Probability a clicked candidate outranks an unclicked one, within this impression."""
    # I use the rank-comparison definition of AUC rather than integrating a ROC curve: build
    # the full clicked x unclicked matrix of "did the clicked one win?" and average it. That
    # mean IS the probability, and with pools of a few dozen candidates the matrix is tiny.
    ranks = ranks_of(scores)
    return float((ranks[~labels][None, :] > ranks[labels][:, None]).mean())


def mrr(scores: np.ndarray, labels: np.ndarray) -> float:
    # Reciprocal of the rank of the FIRST clicked article, hence .min() over clicked ranks.
    # An impression with several clicks is credited for the one it surfaced highest.
    return float(1.0 / ranks_of(scores)[labels].min())


def ndcg(scores: np.ndarray, labels: np.ndarray, k: int) -> float:
    # Binary relevance: gain 1 for a clicked article, 0 otherwise.
    gains = labels.astype(np.float64)
    top = np.argsort(-scores, kind="stable")[:k]
    # Discount starts at log2(2)=1 for rank 1, so the top slot is undiscounted and each
    # lower slot is worth progressively less. That is what makes this rank-sensitive
    # where plain precision@k is not.
    discount = 1.0 / np.log2(np.arange(2, len(top) + 2))
    actual = float((gains[top] * discount).sum())

    # Ideal DCG: the same gains under a perfect ranking (all clicks first). Dividing by it
    # normalises to [0,1] so impressions with different click counts stay comparable.
    best = np.sort(gains)[::-1][:k]
    ideal = float((best * (1.0 / np.log2(np.arange(2, len(best) + 2)))).sum())
    return actual / ideal if ideal > 0 else 0.0


METRICS = {
    "auc": auc,
    "mrr": mrr,
    "ndcg@5": lambda s, y: ndcg(s, y, 5),
    "ndcg@10": lambda s, y: ndcg(s, y, 10),
}


def per_impression(scores: list, labels: list) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Per-impression value of every metric, plus the mask of impressions kept."""
    # An impression where everything (or nothing) was clicked has no pair to rank against,
    # so AUC is undefined there. I drop those rather than scoring them 0 or 1, which would
    # move the average without saying anything about ranking quality. `keep` is returned so
    # slices and bootstrap samples index the same surviving impressions.
    keep = np.array([y.any() and not y.all() for y in labels])
    out = {}
    for name, fn in METRICS.items():
        out[name] = np.array(
            [fn(s, y) for s, y, ok in zip(scores, labels, keep) if ok], dtype=np.float64
        )
    return out, keep


def recall_at_k(retrieved: pl.Series, clicked: pl.Series, ks: tuple[int, ...],
                keep: np.ndarray) -> dict[int, np.ndarray]:
    """Per-impression recall@K for the full-corpus retrieval track.

    Recall is the share of an impression's clicked articles that the retriever surfaced in
    its top K, averaged over impressions — the definition the brief asks for ("how many
    ground-truth clicked articles appear in the top-K candidates").

    Cold-start impressions retrieve nothing and score 0 rather than being dropped: a
    retriever that cannot serve a user has failed for that user, and excluding them would
    quietly report the recall of only the users we could handle.

    `keep` is the same mask the ranking metrics use, so slices line up across the report.

    Stays in Polars deliberately. Materialising these lists in Python costs ~5 GB per
    system at ebnerd_small (245k impressions x 200 ids) and OOMs a 15 GB machine; the
    set intersection runs in Rust and only the one float per impression crosses back.
    """
    rows = pl.DataFrame({"retrieved": retrieved, "clicked": clicked}).filter(keep)
    truth_size = pl.col("clicked").list.len()
    return {
        k: rows.select(
            pl.col("retrieved").list.head(k)
            .list.set_intersection(pl.col("clicked"))
            .list.len() / truth_size
        ).to_series().to_numpy().astype(np.float64)
        for k in ks
    }
