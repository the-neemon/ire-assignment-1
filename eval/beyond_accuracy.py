"""Diversity, novelty and coverage over the top-k the system actually recommends.

Accuracy alone rewards a system that shows everyone the same few popular articles, which
is a bad news product. These three say something different about the same ranking:

  diversity  intra-list dissimilarity — do the top-k span different categories, or are they
             ten variations on one story? Mean pairwise 0/1 category dissimilarity.
  novelty    mean self-information -log2(p) of the recommended items, where p is the item's
             click share in *train*. Recommending the obvious scores low.
  coverage   share of the catalogue that ever appears in any top-k. A system can look
             accurate while only ever surfacing 2% of the corpus.

Novelty uses train click counts only, so it never sees the split being evaluated.
"""

import numpy as np

TOP_K = 10


def _top_ids(candidates: list[str], scores: np.ndarray, k: int) -> list[str]:
    return [candidates[i] for i in np.argsort(-scores, kind="stable")[:k]]


def intra_list_diversity(top_ids: list[str], category_of: dict[str, str]) -> float:
    """Fraction of top-k pairs drawn from different categories."""
    # Category equality is my dissimilarity function, so this is the share of the k*(k-1)/2
    # pairs that differ. 1.0 means every slot is a different section, 0.0 means the whole
    # list is one topic. I use categories rather than embedding distance so the number stays
    # interpretable and does not depend on which encoder the ablation happened to pick.
    cats = [category_of.get(a) for a in top_ids]
    if len(cats) < 2:
        return 0.0
    unlike = sum(
        cats[i] != cats[j] for i in range(len(cats)) for j in range(i + 1, len(cats))
    )
    return unlike / (len(cats) * (len(cats) - 1) / 2)


def novelty(top_ids: list[str], self_information: dict[str, float], default: float) -> float:
    return float(np.mean([self_information.get(a, default) for a in top_ids]))


def self_information_from(train_clicked: list[list[str]]) -> tuple[dict[str, float], float]:
    """-log2(click share) per article, from train only, plus the value for unseen items."""
    counts: dict[str, int] = {}
    for clicked in train_clicked:
        for a in clicked:
            counts[a] = counts.get(a, 0) + 1
    total = sum(counts.values())
    # -log2(p) is self-information: a popular article carries little (everyone sees it), a
    # rare one carries a lot. Averaging it over the top-k is the standard novelty measure,
    # and the log is what stops one blockbuster article from dominating the average.
    table = {a: -np.log2(c / total) for a, c in counts.items()}
    # An article never clicked in train is maximally novel; cap at the rarest observed.
    unseen = -np.log2(1.0 / (total + 1))
    return table, float(unseen)


def evaluate(candidates: list, scores: list, category_of, self_information, unseen,
             catalogue_size: int, k: int = TOP_K):
    """Per-impression diversity and novelty, plus one corpus-level coverage number."""
    diversity, novel = [], []
    surfaced: set[str] = set()
    for cand, score in zip(candidates, scores):
        top = _top_ids(cand, np.asarray(score, dtype=np.float64), k)
        surfaced.update(top)
        diversity.append(intra_list_diversity(top, category_of))
        novel.append(novelty(top, self_information, unseen))
    return {
        "diversity": np.array(diversity),
        "novelty": np.array(novel),
        "coverage": len(surfaced) / catalogue_size,
    }
