"""Semantic counterpart to retrieval/bm25.py — same two tracks, same output shape.

Deliberately mirrors bm25.py: same CLI, same query-deduplication pass, same file naming.
Only the scorer differs, so the lexical and semantic axes stay directly comparable.

  re-rank    cosine between the user vector and each candidate in the given pool
  retrieval  FAISS inner-product search over the whole corpus for the top-K

The user vector is the mean of the L2-normalised vectors of their last `history_len` clicked
articles. History is guaranteed strictly earlier than the impression by pipeline.split.

Article vectors come from whichever source the dataset has:
  EB-NeRD  the organisers' 300-d word2vec document vectors (config `embeddings`), picked
           over bert_base_multilingual_cased by the val-only ablation in NOTES.md
  MIND     encoded here with a sentence-transformers model (config `model`) and cached
           to data/processed/<dataset>/embeddings.parquet, so encoding happens once

    python -m retrieval.embeddings
    python -m retrieval.embeddings mind_small --splits test
    python -m retrieval.embeddings ebnerd_demo --embeddings <other.parquet>   # encoder ablation

Writes, per dataset and split:
    emb_<split>.parquet            impression_id, emb        aligned to `candidates`
    retrieval_emb_<split>.parquet  impression_id, retrieved  top-K ids, best first
"""

import argparse
from collections import defaultdict
from pathlib import Path

import faiss
import numpy as np
import polars as pl
import yaml
from tqdm import tqdm

from retrieval.bm25 import OVERFETCH, TOP_K

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"

SEARCH_BATCH = 4096


def _encode_corpus(articles: pl.DataFrame, model_name: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    texts = (
        articles.select(
            pl.concat_str(
                [pl.col("title").fill_null(""), pl.col("abstract").fill_null("")],
                separator=" ",
            )
        )
        .to_series()
        .to_list()
    )
    print(f"  encoding {len(texts):,} articles with {model_name} (CPU)")
    model = SentenceTransformer(model_name, device="cpu")
    return model.encode(
        texts, batch_size=256, convert_to_numpy=True, show_progress_bar=True
    ).astype(np.float32)


def _unnest(column: pl.Series, rows: int) -> np.ndarray:
    """A List(Float) column as a dense (rows, dim) float32 array.

    Deliberately not `np.vstack(column.to_list())`: that boxes every scalar into a Python
    float on the way through and peaks at 5.8 GB to build a 385 MB array (measured on
    EB-NeRD's 125,541 x 768 provided vectors).
    """
    return column.explode().to_numpy().astype(np.float32).reshape(rows, len(column[0]))


def load_vectors(name: str, cfg: dict, articles: pl.DataFrame) -> np.ndarray:
    """Article vectors, L2-normalised, in the same row order as `articles`."""
    if cfg.get("embeddings"):
        wanted = articles["article_id"].to_list()
        table = (
            pl.scan_parquet(ROOT / cfg["embeddings"])
            .with_columns(pl.col("article_id").cast(pl.String))
            .filter(pl.col("article_id").is_in(wanted))
            .collect()
        )
        column = next(c for c in table.columns if c != "article_id")
        found = dict(zip(table["article_id"], range(table.height)))
        missing = [a for a in wanted if a not in found]
        assert not missing, f"{len(missing)} articles have no provided embedding"
        raw = _unnest(table[column], table.height)
        vectors = raw[[found[a] for a in wanted]]
        print(f"  provided embeddings: {vectors.shape[0]:,} x {vectors.shape[1]}")
    else:
        cache = PROC / name / "embeddings.parquet"
        if cache.exists():
            table = pl.read_parquet(cache)
            assert table["article_id"].to_list() == articles["article_id"].to_list(), (
                "cached embeddings do not match the current corpus; delete "
                f"{cache} to re-encode"
            )
            vectors = _unnest(table["vector"], table.height)
            print(f"  cached embeddings: {vectors.shape[0]:,} x {vectors.shape[1]}")
        else:
            vectors = _encode_corpus(articles, cfg["model"])
            pl.DataFrame({
                "article_id": articles["article_id"],
                "vector": [v.tolist() for v in vectors],
            }).write_parquet(cache)
            print(f"  encoded and cached to {cache}")

    return vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)


def score_split(impressions, articles, vectors, position, published, history_len):
    """One pass over distinct histories, filling both tracks."""
    # Same deduplication idea as bm25.py, but keyed on the history tuple itself rather than
    # rendered query text, since here the history IS the input. Tuples so they can be dict keys.
    histories = [tuple(h[-history_len:]) for h in impressions["history"].to_list()]

    order: dict[tuple, int] = {}
    per_impression = []
    for h in histories:
        per_impression.append(order.setdefault(h, len(order)))
    groups: dict[int, list[int]] = defaultdict(list)
    for row, q_id in enumerate(per_impression):
        groups[q_id].append(row)
    print(f"    {len(order):,} distinct histories for {impressions.height:,} impressions")

    # Mean of the history vectors, renormalised. Cold start stays all-zero, which scores
    # every candidate 0 rather than inventing a ranking.
    # I represent a user as the centroid of what they read: mean-pool their history vectors.
    # Crude but strong, and it needs no training, which keeps this a pure Component-1 system.
    users = np.zeros((len(order), vectors.shape[1]), dtype=np.float32)
    for history, q_id in order.items():
        rows = [position[a] for a in history if a in position]
        if rows:
            users[q_id] = vectors[rows].mean(axis=0)
    # Re-normalise after averaging: the mean of unit vectors is not itself unit length.
    users /= np.linalg.norm(users, axis=1, keepdims=True) + 1e-9

    # IndexFlatIP is inner product, and both sides are L2-normalised, so inner product IS
    # cosine similarity here. Flat means exact (no approximation error) which is affordable
    # at ~125k vectors; IVF/PQ is the scaling story in the design note, not a need yet.
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    n_fetch = min(TOP_K * OVERFETCH, vectors.shape[0])
    top = np.empty((len(order), n_fetch), dtype=np.int64)
    for start in tqdm(range(0, len(order), SEARCH_BATCH), desc="    searching", leave=False):
        chunk = users[start:start + SEARCH_BATCH]
        top[start:start + len(chunk)] = index.search(chunk, n_fetch)[1]

    candidates = impressions["candidates"].to_list()
    timestamps = impressions["timestamp"].to_list()
    article_ids = articles["article_id"].to_numpy()
    cand_scores: list = [None] * impressions.height
    retrieved: list = [None] * impressions.height

    for q_id, rows in groups.items():
        user = users[q_id]
        # A cold-start user's vector stayed all-zero above, so every score would be 0 and any
        # "ranking" would be arbitrary. I detect that here and return nothing retrieved.
        cold = not user.any()
        for row in rows:
            # Re-rank track: one matrix-vector product of the pool's vectors against the user.
            cand_scores[row] = (vectors[[position[a] for a in candidates[row]]] @ user).astype(np.float32)
            if cold:
                retrieved[row] = []
                continue
            hits = top[q_id]
            if published is not None:
                hits = hits[published[hits] <= np.datetime64(timestamps[row])]
            retrieved[row] = article_ids[hits[:TOP_K]].tolist()

    return cand_scores, retrieved


def run(name: str, cfg: dict, splits: list[str]) -> None:
    print(f"\n{name}")
    articles = pl.read_parquet(PROC / name / "articles.parquet")
    vectors = load_vectors(name, cfg, articles)

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
            impressions, articles, vectors, position, published, cfg["history_len"]
        )

        pl.DataFrame({
            "impression_id": impressions["impression_id"],
            "emb": [s.tolist() for s in cand_scores],
        }).write_parquet(PROC / name / f"emb_{split}.parquet")
        pl.DataFrame({
            "impression_id": impressions["impression_id"],
            "retrieved": retrieved,
        }).write_parquet(PROC / name / f"retrieval_emb_{split}.parquet")

        clicked = impressions["clicked"].to_list()
        hit = sum(bool(set(c) & set(r)) for c, r in zip(clicked, retrieved) if c)
        print(f"    recall@{TOP_K} (full-corpus retrieval): {hit / impressions.height:.4f}")


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="*", default=list(config))
    parser.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    parser.add_argument(
        "--embeddings",
        help="article-vector parquet to use instead of the config's; the encoder ablation "
             "runs the same pipeline once per candidate encoder through this flag",
    )
    args = parser.parse_args()

    for name in args.datasets:
        cfg = config[name]
        if args.embeddings:
            cfg = {**cfg, "embeddings": args.embeddings}
        run(name, cfg, args.splits)


if __name__ == "__main__":
    main()
