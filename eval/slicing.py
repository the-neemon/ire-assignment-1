"""Impression slices, so a headline average cannot hide a system that fails a subgroup.

cold vs warm — by history length. "Empty history" is deliberately *not* the definition:
EB-NeRD demo has zero such users (median history 258), so it would select an empty slice and
silently report nothing. A per-dataset bottom-decile threshold works on both, and the
threshold is reported alongside the numbers so the slices stay interpretable.

head vs tail — by how often the clicked article was clicked in *train*. Tail impressions are
where content-based retrieval has to earn its keep; popularity shortcuts cannot help there.
Train-only counts, so the slice definition never sees the split being evaluated.
"""

import numpy as np

COLD_PERCENTILE = 10.0
HEAD_PERCENTILE = 80.0


def by_history_length(history_lengths: np.ndarray) -> tuple[dict[str, np.ndarray], float]:
    # A relative threshold (bottom decile), not an absolute one, because "cold" means
    # something different per dataset: EB-NeRD's median history is 258 clicks, so any fixed
    # cutoff I hard-coded would select everything on one dataset and nothing on the other.
    # I return the threshold so the report can state what "cold" actually meant.
    threshold = float(np.percentile(history_lengths, COLD_PERCENTILE))
    cold = history_lengths <= threshold
    slices = {"cold": cold, "warm": ~cold}
    if (history_lengths == 0).any():
        slices["zero_history"] = history_lengths == 0
    return slices, threshold


def by_article_popularity(clicked: list[list[str]], train_counts: dict[str, int]):
    """Head/tail by the train click count of the impression's clicked article(s)."""
    # Counts come from TRAIN only. If I derived popularity from the split being evaluated,
    # the slice definition would itself be a form of label leakage.
    popularity = np.array(
        [max((train_counts.get(a, 0) for a in c), default=0) for c in clicked],
        dtype=np.float64,
    )
    # Percentile over articles actually seen in train. Including the zeros would drag the
    # threshold to 0 on a long-tailed corpus and put nearly everything in "head".
    observed = popularity[popularity > 0]
    threshold = float(np.percentile(observed, HEAD_PERCENTILE)) if observed.size else 0.0
    head = popularity >= threshold
    return {"head": head, "tail": ~head}, threshold


def train_click_counts(train_clicked: list[list[str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for clicked in train_clicked:
        for a in clicked:
            counts[a] = counts.get(a, 0) + 1
    return counts
