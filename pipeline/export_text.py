"""Export the text to be encoded, and nothing else, for the Colab/Kaggle encoder.

The article ids are taken from the *same* files the pipeline reads, not re-derived from raw
archives — so the vectors that come back are guaranteed to key against the corpus the loaders
expect, with no chance of an id-format drift between here and there.

Writes data/encode_inputs/<name>.parquet with exactly `article_id` (String) and `text`
(String), zstd-compressed. Upload those to Kaggle; encode; bring the vectors back; point
`configs/datasets.yaml` at them. See notebooks/encode_articles.ipynb.

    python -m pipeline.export_text
"""
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/encode_inputs"
OUT.mkdir(parents=True, exist_ok=True)

TEXT = pl.concat_str([pl.col("title").fill_null(""),
                      pl.col("abstract").fill_null("")], separator=" ").alias("text")


def write(name: str, df: pl.DataFrame) -> None:
    df = df.select(pl.col("article_id").cast(pl.String), TEXT)
    path = OUT / f"{name}.parquet"
    df.write_parquet(path, compression="zstd")
    chars = df["text"].str.len_chars()
    print(f"{name:<20} {df.height:>8,} rows  {path.stat().st_size/1e6:>6.1f} MB  "
          f"median {chars.median():>4.0f} chars, p95 {chars.quantile(0.95):>5.0f}")


# --- the two corpora the offline report uses -------------------------------------------
for ds in ["ebnerd_small", "mind_small"]:
    write(ds, pl.read_parquet(ROOT / f"data/processed/{ds}/articles.parquet",
                              columns=["article_id", "title", "abstract"]))

# --- the two the leaderboard needs, only if we rebuild submissions ----------------------
eb = ROOT / "data/interim/ebnerd_testset/ebnerd_testset/articles.parquet"
if eb.exists():
    write("ebnerd_full", pl.read_parquet(eb, columns=["article_id", "title", "subtitle"])
          .rename({"subtitle": "abstract"}))

mind = ROOT / "data/interim/MINDlarge_test/MINDlarge_test/news.tsv"
if mind.exists():
    write("mindlarge_test", pl.read_csv(
        mind, separator="\t", has_header=False, quote_char=None,
        new_columns=["article_id", "category", "subcategory", "title", "abstract",
                     "url", "title_entities", "abstract_entities"],
    ).select("article_id", "title", "abstract"))

print(f"\nupload these -> {OUT}")
