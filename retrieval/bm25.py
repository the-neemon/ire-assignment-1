"""BM25 over article text, on the two tracks the assignment asks for.

  re-rank    score the candidate pool the log already shows for an impression.
             Comparable to the leaderboards, which rank within the given pool.
  retrieval  ignore the pool and pull the top-K from the whole corpus.
             This is the "candidate generation to a few hundred" half of the spec.

The query for both is the user's recent click history: the titles of their last
HISTORY_LEN clicked articles, concatenated. History is already guaranteed strictly
earlier than the impression by pipeline.split, so the query cannot leak.

Both tracks come out of a single scoring pass. Queries are deduplicated first — history
is constant per user within a split, so the ~230k MIND impressions collapse to far fewer
distinct queries, and BM25 runs once per distinct query rather than once per impression.

    python -m retrieval.bm25                       # both datasets, all splits
    python -m retrieval.bm25 ebnerd_demo --fields title

Writes, per dataset and split:
    bm25_<split>.parquet       impression_id, bm25        aligned to `candidates`
    retrieval_<split>.parquet  impression_id, retrieved   top-K ids, best first
"""

import argparse
from collections import defaultdict
from pathlib import Path

import bm25s
import numpy as np
import polars as pl
import Stemmer
import yaml
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"

HISTORY_LEN = 30   # most recent clicks forming the query; news interest decays fast
TOP_K = 200        # "a few hundred candidates"
OVERFETCH = 3      # fetch TOP_K*OVERFETCH before the publication-date filter thins it

FIELDS = {
    "title": ("title",),
    "title_abstract": ("title", "abstract"),
    "title_abstract_body": ("title", "abstract", "body"),
}


def document_text(articles: pl.DataFrame, fields: tuple[str, ...]) -> list[str]:
    present = [f for f in fields if articles[f].null_count() < articles.height]
    missing = set(fields) - set(present)
    if missing:
        print(f"  note: {'/'.join(sorted(missing))} is empty for this dataset, skipping")
    return (
        articles.select(
            pl.concat_str([pl.col(f).fill_null("") for f in present], separator=" ")
        )
        .to_series()
        .to_list()
    )


def stopwords_for(cfg: dict):
    """bm25s ships lists for some languages only; others come from configs/."""
    if cfg.get("stopwords_file"):
        lines = (ROOT / cfg["stopwords_file"]).read_text().splitlines()
        return [w for w in (ln.strip() for ln in lines) if w and not w.startswith("#")]
    return cfg.get("stopwords")


def build_index(articles: pl.DataFrame, cfg: dict, fields: tuple[str, ...]):
    # Stemming and stopwords are per-language (EB-NeRD is Danish, MIND is English), so both
    # come from the dataset config. Getting this wrong silently degrades BM25 rather than
    # erroring: a Danish corpus stemmed as English just matches worse.
    stemmer = Stemmer.Stemmer(cfg["language"])
    texts = document_text(articles, fields)
    tokens = bm25s.tokenize(
        texts, stopwords=stopwords_for(cfg), stemmer=stemmer, show_progress=False
    )
    index = bm25s.BM25()
    index.index(tokens, show_progress=False)
    return index, stemmer


def build_queries(impressions: pl.DataFrame, title_of: dict[str, str]) -> list[str]:
    """Last HISTORY_LEN clicked titles per impression. Empty for cold-start users."""
    # I treat "what this user recently read" as the query and the corpus as documents, which
    # turns recommendation into ordinary ad-hoc retrieval. Titles only, and only the most
    # recent HISTORY_LEN, because news interest decays fast and older clicks add drift.
    return [
        " ".join(title_of.get(a, "") for a in hist[-HISTORY_LEN:])
        for hist in impressions["history"].to_list()
    ]


def score_split(index, stemmer, cfg, impressions, articles, position, published):
    """One pass over distinct queries, filling both tracks."""
    queries = build_queries(impressions, dict(zip(articles["article_id"], articles["title"])))

    # A user's history is fixed within a split, so the same query text recurs across all of
    # that user's impressions. I map each distinct query to an id, then invert it into
    # query -> [rows that share it], so BM25 scores each query once and I fan the result out.
    # setdefault gives me "look up or assign the next id" in one step.
    order: dict[str, int] = {}
    per_impression = []
    for q in queries:
        per_impression.append(order.setdefault(q, len(order)))
    groups: dict[int, list[int]] = defaultdict(list)
    for row, q_id in enumerate(per_impression):
        groups[q_id].append(row)
    print(f"    {len(order):,} distinct queries for {impressions.height:,} impressions")

    tokenized = bm25s.tokenize(
        list(order), stopwords=stopwords_for(cfg), stemmer=stemmer,
        return_ids=False, show_progress=False,
    )

    candidates = impressions["candidates"].to_list()
    timestamps = impressions["timestamp"].to_list()
    article_ids = articles["article_id"].to_numpy()
    n_fetch = min(TOP_K * OVERFETCH, len(article_ids))

    cand_scores: list = [None] * impressions.height
    retrieved: list = [None] * impressions.height

    for q_id, tokens in enumerate(tqdm(tokenized, desc="    scoring", unit="q", leave=False)):
        rows = groups[q_id]
        if not tokens:
            # Cold start: no history, so BM25 has no query. Zero scores and an empty
            # retrieval, rather than an arbitrary ranking that would look like a result.
            for row in rows:
                cand_scores[row] = np.zeros(len(candidates[row]), dtype=np.float32)
                retrieved[row] = []
            continue

        # One dense score vector over the whole corpus, which both tracks then read from.
        scores = index.get_scores(tokens)
        # argpartition to find the top n_fetch is O(corpus); fully sorting 125k scores when
        # I only need 600 of them would not be. I sort only that small slice afterwards.
        top = np.argpartition(-scores, n_fetch - 1)[:n_fetch]
        top = top[np.argsort(-scores[top])]

        for row in rows:
            # Re-rank track: just look up the pool's articles in the same score vector.
            cand_scores[row] = scores[[position[a] for a in candidates[row]]].astype(np.float32)
            hits = top
            if published is not None:
                # An article published after the impression could not have been shown.
                # I over-fetched by OVERFETCH precisely so this filter still leaves TOP_K.
                hits = hits[published[hits] <= np.datetime64(timestamps[row])]
            retrieved[row] = article_ids[hits[:TOP_K]].tolist()

    return cand_scores, retrieved


def run(name: str, cfg: dict, fields: tuple[str, ...], splits: list[str]) -> None:
    print(f"\n{name}  fields={'+'.join(fields)}")
    articles = pl.read_parquet(PROC / name / "articles.parquet")
    index, stemmer = build_index(articles, cfg, fields)
    print(f"  indexed {articles.height:,} articles")

    position = {a: i for i, a in enumerate(articles["article_id"])}
    published = None
    if articles["published_time"].null_count() < articles.height:
        published = articles["published_time"].to_numpy()
    else:
        print("  note: no publication dates; retrieval cannot filter unpublished articles")

    for split in splits:
        impressions = pl.read_parquet(PROC / name / f"impressions_{split}.parquet")
        print(f"  {split}: {impressions.height:,} impressions")
        cand_scores, retrieved = score_split(
            index, stemmer, cfg, impressions, articles, position, published
        )

        pl.DataFrame({
            "impression_id": impressions["impression_id"],
            "bm25": [s.tolist() for s in cand_scores],
        }).write_parquet(PROC / name / f"bm25_{split}.parquet")
        pl.DataFrame({
            "impression_id": impressions["impression_id"],
            "retrieved": retrieved,
        }).write_parquet(PROC / name / f"retrieval_{split}.parquet")

        # Recall@K here is a build-time sanity signal, not the reported metric.
        clicked = impressions["clicked"].to_list()
        hit = sum(
            bool(set(c) & set(r)) for c, r in zip(clicked, retrieved) if c
        )
        print(f"    recall@{TOP_K} (full-corpus retrieval): {hit / impressions.height:.4f}")


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="*", default=list(config))
    parser.add_argument("--fields", choices=list(FIELDS), default="title_abstract")
    parser.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    args = parser.parse_args()

    for name in args.datasets:
        run(name, config[name], FIELDS[args.fields], args.splits)


if __name__ == "__main__":
    main()
