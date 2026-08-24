"""Temporal train/val/test split into one normalized schema for both datasets.

EB-NeRD and MIND describe the same thing in different shapes. Everything downstream
(BM25, embeddings, eval) reads the normalized output, so it has exactly one code path.

    data/processed/<dataset>/impressions_{train,val,test}.parquet
        impression_id       Int64
        user_id             String
        timestamp           Datetime         impression time
        candidates          List(String)     the pool shown, article ids
        clicked             List(String)     subset of candidates that was clicked
        history             List(String)     this user's prior clicks, strictly earlier
        history_timestamps  List(Datetime)   EB-NeRD only; MIND ships no per-item
                                             history timestamps, so this is null there
        recency_seconds     Float64          seconds since this user's most recent prior
                                             click; null where genuinely unknown

    data/processed/<dataset>/articles.parquet
        article_id  String
        title       String
        abstract    String     EB-NeRD subtitle / MIND abstract
        body        String     EB-NeRD only; MIND-small ships no body text
        category    String
        entities    List(String)  named-entity surface forms (EB-NeRD ner_clusters /
                                  MIND title+abstract entity Labels)
        published_time Datetime   EB-NeRD only; MIND news.tsv carries no date

Article ids are strings in both datasets so the two share a schema; EB-NeRD's integer
ids are cast on the way in.

    python -m pipeline.split                # both datasets
    python -m pipeline.split ebnerd_demo
"""

import argparse
from datetime import datetime
from pathlib import Path

import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
OUT = ROOT / "data/processed"

MIND_BEHAVIORS = ["impression_id", "user_id", "time", "history", "impressions"]
MIND_NEWS = ["article_id", "category", "subcategory", "title", "abstract", "url",
             "title_entities", "abstract_entities"]


# --------------------------------------------------------------------- EB-NeRD

def _ebnerd_block(root: Path) -> pl.DataFrame:
    """One provided block (train or validation) -> normalized impressions."""
    behaviors = pl.read_parquet(root / "behaviors.parquet")
    history = pl.read_parquet(root / "history.parquet")

    # EB-NeRD keeps ids as integers and MIND as strings. I cast everything to String here so
    # one normalised schema serves both, at the cost of a little memory.
    ids = pl.element().cast(pl.String)
    return (
        # History is a separate file keyed by user, so I join it onto each impression. It is
        # a left join because a user with no prior activity must survive as a cold start
        # rather than vanish from the split.
        behaviors.join(history, on="user_id", how="left")
        .select(
            pl.col("impression_id").cast(pl.Int64),
            pl.col("user_id").cast(pl.String),
            pl.col("impression_time").alias("timestamp"),
            pl.col("article_ids_inview").list.eval(ids).alias("candidates"),
            pl.col("article_ids_clicked").list.eval(ids).alias("clicked"),
            pl.col("article_id_fixed").list.eval(ids).alias("history"),
            pl.col("impression_time_fixed").alias("history_timestamps"),
        )
    )


def load_ebnerd(cfg: dict) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    early = _ebnerd_block(ROOT / cfg["early_root"])
    test = _ebnerd_block(ROOT / cfg["test_root"])
    articles = pl.read_parquet(ROOT / cfg["articles"]).select(
        pl.col("article_id").cast(pl.String),
        pl.col("title"),
        pl.col("subtitle").alias("abstract"),
        pl.col("body"),
        pl.col("category_str").alias("category"),
        # Named-entity surface forms. EB-NeRD ships them pre-extracted (86% of articles);
        # MIND ships JSON that _mind_news parses to the same List(String) shape.
        pl.col("ner_clusters").alias("entities"),
        pl.col("published_time"),
        # Lifetime aggregates computed over the whole collection period, so they embed the
        # future and are not available at serving time. Carried only so the harness can
        # report metrics with and without them (an organiser requirement); no scorer that
        # claims to be servable may read these.
        pl.col("total_inviews"),
        pl.col("total_pageviews"),
        pl.col("total_read_time"),
    )
    return early, test, articles


# ------------------------------------------------------------------------ MIND

def _mind_block(root: Path) -> pl.DataFrame:
    behaviors = pl.read_csv(
        root / "behaviors.tsv", separator="\t", has_header=False,
        new_columns=MIND_BEHAVIORS, quote_char=None,
    ).with_row_index("row")

    # MIND packs the whole impression into one string, "N55689-1 N35729-0", where the suffix
    # is the label. I explode it to one row per candidate, read the suffix, then regroup, so
    # the parsing happens in Polars rather than a Python loop over 230k rows.
    # "N55689-1 N35729-0" -> candidates + the clicked subset
    pairs = (
        behaviors.select("row", pl.col("impressions").str.split(" ").alias("pair"))
        .explode("pair")
        .with_columns(
            pl.col("pair").str.split("-").list.first().alias("article_id"),
            (pl.col("pair").str.split("-").list.last() == "1").alias("was_clicked"),
        )
    )
    labelled = pairs.group_by("row").agg(
        pl.col("article_id").alias("candidates"),
        pl.col("article_id").filter(pl.col("was_clicked")).alias("clicked"),
    )

    return (
        behaviors.join(labelled, on="row", how="left")
        .select(
            pl.col("impression_id").cast(pl.Int64),
            pl.col("user_id").cast(pl.String),
            pl.col("time").str.strptime(pl.Datetime, "%m/%d/%Y %I:%M:%S %p").alias("timestamp"),
            pl.col("candidates"),
            pl.col("clicked"),
            # A user with no prior clicks is a cold start, not a missing value — but
            # "".split(" ") is [""], not [], so drop the empty token or every cold-start
            # user gets a phantom one-item history and lands in the wrong eval slice.
            pl.col("history").fill_null("").str.split(" ")
            .list.eval(pl.element().filter(pl.element() != "")).alias("history"),
            pl.lit(None, dtype=pl.List(pl.Datetime)).alias("history_timestamps"),
        )
    )


def _entity_labels(column: str) -> pl.Expr:
    """MIND ships entities as a JSON array per field; we keep the surface labels.

    `json_decode` needs the shape up front, and we only want one field of it, so the
    struct is declared with just `Label` — the rest of each record is discarded.
    """
    dtype = pl.List(pl.Struct({"Label": pl.String}))
    return (
        pl.col(column).fill_null("[]").str.json_decode(dtype)
        .list.eval(pl.element().struct.field("Label"))
    )


def _mind_news(root: Path) -> pl.DataFrame:
    return pl.read_csv(
        root / "news.tsv", separator="\t", has_header=False,
        new_columns=MIND_NEWS, quote_char=None,
    ).select(
        "article_id", "title", "abstract",
        pl.lit(None, dtype=pl.String).alias("body"),
        "category",
        # Title and abstract entities are one pool; duplicates across the two are
        # the same entity mentioned twice, not two entities.
        pl.concat_list(_entity_labels("title_entities"),
                       _entity_labels("abstract_entities"))
        # maintain_order, or the deduplication is hash-ordered and the file stops
        # being byte-identical between runs.
        .list.unique(maintain_order=True).alias("entities"),
        pl.lit(None, dtype=pl.Datetime).alias("published_time"),
        # MIND ships no lifetime aggregates; kept for schema parity with EB-NeRD.
        pl.lit(None, dtype=pl.Int32).alias("total_inviews"),
        pl.lit(None, dtype=pl.Int32).alias("total_pageviews"),
        pl.lit(None, dtype=pl.Float32).alias("total_read_time"),
    )


def load_mind(cfg: dict) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    early_root, test_root = ROOT / cfg["early_root"], ROOT / cfg["test_root"]
    early = _mind_block(early_root)
    test = _mind_block(test_root)
    # The two splits ship different news files; 13,956 articles appear only in dev.
    # Indexing either alone leaves part of the test corpus unreachable.
    articles = pl.concat([_mind_news(early_root), _mind_news(test_root)]).unique(
        subset="article_id", keep="first"
    )
    return early, test, articles


LOADERS = {"ebnerd": load_ebnerd, "mind": load_mind}


# ------------------------------------------------------------------- user features

def with_recency(df: pl.DataFrame) -> pl.DataFrame:
    """Add `recency_seconds`: how long before this impression the user last clicked.

    Derived here rather than inside either loader, because the definition is the same for
    both datasets and it is built from `history_timestamps`, which the loaders have already
    constrained to precede the impression. That is what makes it leakage-free by
    construction rather than by inspection: the value can only ever look backwards.

    Null means genuinely unknown, never zero:
      * a cold-start user has no prior click, and 0 would read as "clicked just now"
      * MIND ships no per-item history times at all, so no impression there can have one
    """
    if df["history_timestamps"].dtype == pl.Null:
        return df.with_columns(pl.lit(None, dtype=pl.Float64).alias("recency_seconds"))
    return df.with_columns(
        (pl.col("timestamp") - pl.col("history_timestamps").list.max())
        .dt.total_seconds().cast(pl.Float64).alias("recency_seconds")
    )


# ------------------------------------------------------------------- integrity

def check_integrity(splits: dict[str, pl.DataFrame], articles: pl.DataFrame) -> None:
    """Fail loudly on anything that would let future information into a split."""
    train, val, test = splits["train"], splits["val"], splits["test"]

    # These are assertions, not warnings, on purpose: the assignment requires leakage to be
    # prevented in code rather than by discipline, so a violation must stop the build.

    # 1. strict temporal ordering
    bounds = {k: (v["timestamp"].min(), v["timestamp"].max()) for k, v in splits.items()}
    assert bounds["train"][1] < bounds["val"][0], "train overlaps val"
    assert bounds["val"][1] < bounds["test"][0], "val overlaps test"
    print("  [ok] train < val < test, strictly")

    # 2. no future clicks in history
    if train["history_timestamps"].dtype != pl.Null and train["history_timestamps"].null_count() < train.height:
        for name, df in splits.items():
            late = df.filter(
                pl.col("history_timestamps").list.max() >= pl.col("timestamp")
            ).height
            assert late == 0, f"{name}: {late} impressions have history at/after impression time"
        print("  [ok] every history click strictly precedes its impression (per-item)")

        # recency is derived from those same timestamps, so a non-positive value would mean
        # the derivation looked forwards. Checked separately because a sign error here would
        # not trip the check above.
        for name, df in splits.items():
            bad = df.filter(pl.col("recency_seconds") <= 0).height
            assert bad == 0, f"{name}: {bad} impressions have non-positive recency"
        print("  [ok] recency_seconds is strictly positive wherever it is defined")
    else:
        print("  [--] history carries no timestamps; per-item leakage check not possible.")
        print("       Guarantee is structural only (history precedes the log period).")

    # 3. labels must be drawn from the pool shown
    for name, df in splits.items():
        bad = df.filter(
            pl.col("clicked").list.set_difference(pl.col("candidates")).list.len() > 0
        ).height
        assert bad == 0, f"{name}: {bad} impressions clicked outside the candidate pool"
    print("  [ok] clicked is a subset of candidates")

    # 4. candidates must exist in the corpus, and no id may be the empty string —
    #    an empty token is how a cold-start history silently turns into a 1-item one.
    known = set(articles["article_id"])
    for name, df in splits.items():
        for col in ("candidates", "clicked", "history"):
            ids = set(df[col].explode().drop_nulls())
            assert "" not in ids, f"{name}.{col}: contains an empty article id"
            if col == "candidates":
                assert not (ids - known), (
                    f"{name}: {len(ids - known)} candidates absent from articles.parquet"
                )
    print("  [ok] every candidate resolves to an article; no empty ids")

    # 5. articles published after a split's start cannot be retrieved for it.
    #    Only reportable where the corpus carries a date (EB-NeRD).
    if articles["published_time"].null_count() < articles.height:
        future = articles.filter(pl.col("published_time") > bounds["test"][1]).height
        print(f"  [!!] {future} articles published after the test window ends "
              f"({bounds['test'][1]}).")
        print("       Full-corpus retrieval must filter published_time <= impression_time.")
    else:
        print("  [--] corpus has no publication dates; the published-after-impression")
        print("       filter cannot be applied for this dataset.")


# ----------------------------------------------------------------------- driver

def build(name: str, cfg: dict) -> None:
    print(f"\n{name}")
    early, test, articles = LOADERS[cfg["loader"]](cfg)

    val_start = datetime.fromisoformat(cfg["val_start"])
    test_start = datetime.fromisoformat(cfg["test_start"])

    # The temporal split, and the reason nothing here is random. Both datasets already ship
    # a later block that I use untouched as test; I carve val off the END of the earlier
    # block by timestamp. Strict `<` against `>=` on the same cutoff means no impression can
    # land in both, which is the property check_integrity then verifies independently.
    splits = {
        "train": with_recency(early.filter(pl.col("timestamp") < val_start)),
        "val": with_recency(early.filter(pl.col("timestamp") >= val_start)),
        "test": with_recency(test),
    }
    assert splits["test"]["timestamp"].min() >= test_start, (
        f"test block starts before its declared test_start {test_start}"
    )

    check_integrity(splits, articles)

    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    # Sort on a unique key before writing. `unique()` is hash-based and row order after it
    # varies run to run, which would make the pipeline non-reproducible byte-for-byte.
    articles.sort("article_id").write_parquet(out / "articles.parquet")
    total = sum(df.height for df in splits.values())
    for split, df in splits.items():
        (df.sort(["timestamp", "impression_id"])
           .write_parquet(out / f"impressions_{split}.parquet"))
        print(f"  {split:<5} {df.height:>7,} ({df.height / total:5.1%})  "
              f"{df['timestamp'].min()} -> {df['timestamp'].max()}")
    print(f"  articles {articles.height:,} -> {out}")


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="*", default=list(config))
    args = parser.parse_args()

    for name in args.datasets:
        build(name, config[name])


if __name__ == "__main__":
    main()
