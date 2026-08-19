"""Codabench leaderboard submissions for both competitions.

The leaderboards score held-out test sets that are far larger than anything the offline
harness touches — EB-NeRD 13.5M impressions (206M candidate pairs), MIND-large 2.4M — so
this cannot reuse `retrieval/embeddings.py`, which materialises every impression at once.
The scoring *semantics* are identical (mean of the last HISTORY_LEN article vectors,
L2-normalised, cosine against each candidate); only the execution is streamed.

    python -m pipeline.submit ebnerd            -> submissions/ebnerd_predictions.zip
    python -m pipeline.submit mind              -> submissions/mind_prediction.zip
    python -m pipeline.submit ebnerd --limit 50000     smoke test on a prefix

Format, from each competition's Submission Guidelines (fetched from the Codabench API):

    <impression_id> [r1,r2,...,rn]

`ri` is the rank *of the i-th candidate as listed in the test file*, an integer in 1..n
where 1 is the best. Row order must match the test file. The zip must contain the text
file and nothing else — no folders, no __MACOSX.

Only the embedding scorer ships here, on both datasets, because BM25's `get_scores` is dense
over the whole corpus per distinct query and does not survive these sizes (DESIGN_NOTE §10).

**So the leaderboard entry is not the reported headline system, and the gap is not free.**
Offline, `fused` beats embeddings alone by +0.0014 AUC on MIND and +0.0095 on EB-NeRD; on
EB-NeRD embeddings alone also lose to BM25 alone, making the submitted system the weakest of
the three measured. Reported as two different systems rather than letting the better number
stand in for the one actually uploaded — see DESIGN_NOTE §11.

Which article vectors get used comes from `configs/datasets.yaml`, the same key
`retrieval/embeddings.py` reads, so the encoder chosen by the ablation cannot silently
diverge between the report and the submission.
"""

import argparse
import zipfile
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from retrieval.bm25 import HISTORY_LEN

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
INTERIM = ROOT / "data/interim"
OUT = ROOT / "deliverable/submissions"

# Impressions per streamed slice. Peak memory is one slice, not the dataset.
BATCH = 200_000
# Candidate pairs per vectorised dot-product block. A block materialises two
# (PAIR_BLOCK, dim) float32 arrays, so this is the real memory knob: 65536 x 768 x 4 x 2
# is ~400 MB, which is what keeps a 206M-pair run inside a 15 GB machine.
PAIR_BLOCK = 65_536


def ranks_from(scores: np.ndarray) -> np.ndarray:
    """Rank of each candidate, 1 = highest score.

    Stable sort, so equal scores keep the order the test file listed them in and the
    output is reproducible. A cold-start user scores every candidate 0 and therefore
    gets the identity ranking — no ordering is invented from nothing.
    """
    order = np.argsort(-scores, kind="stable")
    out = np.empty(len(scores), dtype=np.int64)
    out[order] = np.arange(1, len(scores) + 1)
    return out


def score_pairs(article_rows: np.ndarray, user_rows: np.ndarray,
                vectors: np.ndarray, users: np.ndarray) -> np.ndarray:
    """Cosine for every (candidate, user) pair, in blocks so the gather stays bounded."""
    out = np.empty(len(article_rows), dtype=np.float32)
    for start in range(0, len(article_rows), PAIR_BLOCK):
        sl = slice(start, start + PAIR_BLOCK)
        # einsum "ij,ij->i" is a ROW-WISE dot product: pair i of the left with pair i of the
        # right. I want 206M individual (candidate, user) dots, not a 206M x 206M matrix,
        # which is what a plain @ would attempt. The fancy-index gather is what actually
        # allocates, so PAIR_BLOCK caps that rather than the arithmetic.
        out[sl] = np.einsum(
            "ij,ij->i", vectors[article_rows[sl]], users[user_rows[sl]]
        )
    return out


def mean_pool(histories: pl.Series, article_row: np.ndarray,
              vectors: np.ndarray, dim: int) -> np.ndarray:
    """User vectors: mean of the last HISTORY_LEN article vectors, L2-normalised.

    Row i corresponds to histories[i]. Users with no usable history stay all-zero, which
    is the cold-start convention the offline scorer uses too.
    """
    users = np.zeros((len(histories), dim), dtype=np.float32)
    for i, history in enumerate(histories):
        if history is None or len(history) == 0:
            continue
        rows = article_row[np.asarray(history[-HISTORY_LEN:], dtype=np.int64)]
        if len(rows):
            users[i] = vectors[rows].mean(axis=0)
    users /= np.linalg.norm(users, axis=1, keepdims=True) + 1e-9
    return users


def write_lines(handle, impression_ids: np.ndarray, scores: np.ndarray,
                lengths: np.ndarray) -> None:
    """Split the flat score array back per impression, rank, and emit one line each."""
    offset = 0
    for imp_id, n in zip(impression_ids, lengths):
        ranks = ranks_from(scores[offset:offset + n])
        offset += n
        handle.write(f"{imp_id} [{','.join(map(str, ranks.tolist()))}]\n")


# ------------------------------------------------------------------------- EB-NeRD

def stream_ebnerd(cfg: dict, limit: int | None):
    root = INTERIM / "ebnerd_testset/ebnerd_testset"
    articles = pl.read_parquet(root / "articles.parquet", columns=["article_id"])
    ids = articles["article_id"].to_numpy().astype(np.int64)

    # Integer ids let us use a lookup array instead of a dict of 125k strings — and,
    # more importantly, keep 206M candidate ids out of Python entirely.
    # A plain array indexed BY article id, holding its row in `vectors`. Ids are dense ints,
    # so this is an O(1) lookup with no hashing and no Python objects, and it vectorises:
    # article_row[flat] resolves millions of candidates in one call.
    article_row = np.full(int(ids.max()) + 1, -1, dtype=np.int64)
    article_row[ids] = np.arange(len(ids))

    vectors = _provided_vectors(cfg, articles)
    dim = vectors.shape[1]
    # Unknown candidates land on a trailing zero row: score 0, no crash, no silent
    # misalignment onto some other article's vector.
    vectors = np.vstack([vectors, np.zeros((1, dim), dtype=np.float32)])
    article_row[article_row < 0] = len(vectors) - 1

    print("  building user vectors from history.parquet")
    history = pl.read_parquet(root / "test/history.parquet",
                              columns=["user_id", "article_id_fixed"])
    users = mean_pool(history["article_id_fixed"], article_row, vectors, dim)
    uids = history["user_id"].to_numpy().astype(np.int64)
    user_row = np.full(int(uids.max()) + 1, len(users), dtype=np.int64)
    user_row[uids] = np.arange(len(users))
    users = np.vstack([users, np.zeros((1, dim), dtype=np.float32)])
    print(f"  {len(users) - 1:,} users, {len(vectors) - 1:,} articles, dim {dim}")
    del history, uids     # ~1 GB of history lists, dead once the means are built

    scan = pl.scan_parquet(root / "test/behaviors.parquet").select(
        "impression_id", "user_id", "article_ids_inview"
    )
    total = scan.select(pl.len()).collect().item()
    if limit:
        total = min(total, limit)

    # Slice pushdown reaches the parquet row groups, so a slice at offset 13M costs the
    # same as one at 0 (measured: 0.05s either way). That is what keeps peak memory flat
    # in the number of impressions instead of linear — collecting the frame first would
    # add ~1 GB of candidate lists before scoring a single row.
    for offset in range(0, total, BATCH):
        batch = scan.slice(offset, min(BATCH, total - offset)).collect()
        lengths = batch["article_ids_inview"].list.len().to_numpy().astype(np.int64)
        flat = batch["article_ids_inview"].explode().to_numpy().astype(np.int64)
        rows = article_row[flat]
        per_user = user_row[batch["user_id"].to_numpy().astype(np.int64)]
        # `flat` is every candidate of every impression concatenated, so I repeat each user
        # index `lengths[i]` times to line the two up element-for-element. `lengths` is what
        # lets write_lines cut the flat score array back into per-impression rows.
        scores = score_pairs(rows, np.repeat(per_user, lengths), vectors, users)
        yield batch["impression_id"].to_numpy(), scores, lengths


def _provided_vectors(cfg: dict, articles: pl.DataFrame) -> np.ndarray:
    """The organisers' provided article vectors, in articles.parquet row order.

    Which file that is comes from the config, so the encoder chosen by the ablation is the
    one the leaderboard run uses — the submission cannot silently diverge from the report.
    """
    table = pl.read_parquet(ROOT / cfg["embeddings"])
    column = next(c for c in table.columns if c != "article_id")
    found = dict(zip(table["article_id"].cast(pl.Int64).to_list(), range(table.height)))
    wanted = articles["article_id"].cast(pl.Int64).to_list()
    missing = [a for a in wanted if a not in found]
    assert not missing, f"{len(missing)} test articles have no provided embedding"

    # explode->to_numpy, not to_list()->vstack. The latter builds 96M boxed Python floats
    # to produce a 385 MB array and peaks at 5.8 GB doing it (measured).
    dim = len(table[column][0])
    raw = table[column].explode().to_numpy().astype(np.float32).reshape(table.height, dim)
    vectors = raw[[found[a] for a in wanted]]
    return vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)


# ---------------------------------------------------------------------------- MIND

def stream_mind(cfg: dict, limit: int | None):
    root = INTERIM / "MINDlarge_test/MINDlarge_test"
    news = pl.read_csv(
        root / "news.tsv", separator="\t", has_header=False, quote_char=None,
        new_columns=["article_id", "category", "subcategory", "title", "abstract",
                     "url", "title_entities", "abstract_entities"],
    ).select("article_id", "title", "abstract")

    vectors = _encoded_vectors(news, cfg["model"])
    dim = vectors.shape[1]
    vectors = np.vstack([vectors, np.zeros((1, dim), dtype=np.float32)])
    article_row = {a: i for i, a in enumerate(news["article_id"])}
    unknown = len(vectors) - 1

    prepared = _mind_parquet(root, article_row, unknown)
    scan = pl.scan_parquet(prepared)
    total = scan.select(pl.len()).collect().item()
    if limit:
        total = min(total, limit)
    print(f"  {total:,} impressions, {len(article_row):,} articles, dim {dim}")

    for offset in range(0, total, BATCH):
        batch = scan.slice(offset, min(BATCH, total - offset)).collect()
        # Histories are already row indices, so deduplication is over tuples of ints.
        # Dedup is per slice: across slices identical histories are recomputed, which is
        # the trade streaming makes for bounded memory. Mean-pooling 30 vectors is cheap.
        order: dict[tuple, int] = {}
        index = np.fromiter(
            (order.setdefault(tuple(h[-HISTORY_LEN:]), len(order))
             for h in batch["history_rows"]),
            dtype=np.int64, count=batch.height,
        )
        users = np.zeros((len(order), dim), dtype=np.float32)
        for key, i in order.items():
            rows = np.asarray(key, dtype=np.int64)
            rows = rows[rows != unknown]
            if len(rows):
                users[i] = vectors[rows].mean(axis=0)
        users /= np.linalg.norm(users, axis=1, keepdims=True) + 1e-9

        lengths = batch["cand_rows"].list.len().to_numpy().astype(np.int64)
        rows = batch["cand_rows"].explode().to_numpy().astype(np.int64)
        scores = score_pairs(rows, np.repeat(index, lengths), vectors, users)
        yield batch["impression_id"].to_numpy(), scores, lengths


def _mind_parquet(root: Path, article_row: dict, unknown: int) -> Path:
    """One-off behaviors.tsv -> parquet, with article ids already resolved to row indices.

    Two reasons this conversion exists rather than reading the TSV directly. CSV has no
    slice pushdown, so streaming it means holding all 2.37M rows — 1.45 GB in Arrow, 3.07 GB
    peak to parse, which OOM-killed the first attempt. And resolving ids here keeps ~93M
    candidate strings out of the scoring loop entirely, the same reason EB-NeRD's Int32 ids
    are handled as a lookup array.
    """
    cache = ROOT / "data/processed/mindlarge_test_behaviors.parquet"
    if cache.exists():
        return cache

    print("  converting behaviors.tsv -> parquet (one-off)")
    ids = pl.Series("a", list(article_row.keys()))
    idx = pl.Series("i", list(article_row.values()), dtype=pl.Int32)
    to_row = pl.element().replace_strict(ids, idx, default=unknown, return_dtype=pl.Int32)

    (pl.scan_csv(root / "behaviors.tsv", separator="\t", has_header=False, quote_char=None,
                 new_columns=["impression_id", "user_id", "time", "history", "impressions"])
       .select(
           pl.col("impression_id").cast(pl.Int64),
           pl.col("history").fill_null("").str.split(" ")
             .list.eval(pl.element().filter(pl.element() != ""))
             .list.eval(to_row).alias("history_rows"),
           pl.col("impressions").str.split(" ").list.eval(to_row).alias("cand_rows"),
       )
       .sink_parquet(cache))
    print(f"  cached to {cache}")
    return cache


def _encoded_vectors(news: pl.DataFrame, model_name: str) -> np.ndarray:
    """MIND-large test has its own corpus, so it needs its own cache."""
    cache = ROOT / "data/processed/mindlarge_test_embeddings.npy"
    if cache.exists():
        vectors = np.load(cache)
        assert len(vectors) == news.height, (
            f"cache has {len(vectors)} vectors for {news.height} articles; delete {cache}"
        )
        print(f"  cached embeddings: {vectors.shape}")
    else:
        from sentence_transformers import SentenceTransformer

        texts = news.select(
            pl.concat_str([pl.col("title").fill_null(""),
                           pl.col("abstract").fill_null("")], separator=" ")
        ).to_series().to_list()
        print(f"  encoding {len(texts):,} articles with {model_name}")
        model = SentenceTransformer(model_name)
        vectors = model.encode(texts, batch_size=256, convert_to_numpy=True,
                               show_progress_bar=True).astype(np.float32)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache, vectors)
        print(f"  cached to {cache}")
    return vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)


# -------------------------------------------------------------------------- driver

TARGETS = {
    # inner filename differs between the two competitions — mind the plural
    "ebnerd": (stream_ebnerd, "predictions.txt", "ebnerd_predictions.zip", "ebnerd_demo"),
    "mind": (stream_mind, "prediction.txt", "mind_prediction.zip", "mind_small"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=list(TARGETS))
    parser.add_argument("--limit", type=int, help="only the first N impressions (smoke test)")
    args = parser.parse_args()

    stream, inner, archive, cfg_key = TARGETS[args.target]
    cfg = yaml.safe_load(CONFIG.read_text())[cfg_key]

    OUT.mkdir(exist_ok=True)
    txt, zip_path = OUT / inner, OUT / archive
    print(f"{args.target} -> {zip_path}")

    written = 0
    with open(txt, "w") as handle:
        for impression_ids, scores, lengths in stream(cfg, args.limit):
            write_lines(handle, impression_ids, scores, lengths)
            written += len(impression_ids)
            print(f"    {written:,} impressions", end="\r", flush=True)
    print(f"    {written:,} impressions written")

    # Nothing but the text file, no directory entries — the guidelines are explicit.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(txt, arcname=inner)
    print(f"  {zip_path.name}  {zip_path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
