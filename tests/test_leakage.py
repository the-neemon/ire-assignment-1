"""No-future-click leakage tests, run against the built artifacts.

`pipeline/split.py` asserts these same properties while building. This file re-checks them
from the outside, reading only `data/processed/`, which is a different and stronger claim:
the build asserts what it *intended* to write, this asserts what is *actually on disk* and
what every downstream stage will therefore read.

    make test           # or: .venv/bin/python -m pytest tests/ -v

Datasets that have not been built are skipped, so this is runnable after a partial pipeline.
"""

from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data/processed"
SPLITS = ("train", "val", "test")

DATASETS = sorted(yaml.safe_load((ROOT / "configs/datasets.yaml").read_text()))


def load(name: str) -> dict[str, pl.DataFrame]:
    """Built impressions for one dataset, or skip if the pipeline has not run for it."""
    missing = [s for s in SPLITS if not (PROC / name / f"impressions_{s}.parquet").exists()]
    if missing:
        pytest.skip(f"{name} not built (missing {', '.join(missing)}); run `make split`")
    return {s: pl.read_parquet(PROC / name / f"impressions_{s}.parquet") for s in SPLITS}


@pytest.fixture(scope="module", params=DATASETS)
def dataset(request) -> tuple[str, dict[str, pl.DataFrame]]:
    # Parametrised over datasets read from the config, so adding a dataset there
    # automatically extends every test below to it rather than silently going unchecked.
    return request.param, load(request.param)


# --------------------------------------------------------------- temporal ordering

def test_splits_are_strictly_ordered_in_time(dataset):
    """train < val < test with no overlap at the boundary.

    A random split would fail this; so would an off-by-one on a cutoff that let a single
    impression sit on both sides.
    """
    name, splits = dataset
    bounds = {s: (df["timestamp"].min(), df["timestamp"].max()) for s, df in splits.items()}

    assert bounds["train"][1] < bounds["val"][0], (
        f"{name}: train ends {bounds['train'][1]} but val starts {bounds['val'][0]}"
    )
    assert bounds["val"][1] < bounds["test"][0], (
        f"{name}: val ends {bounds['val'][1]} but test starts {bounds['test'][0]}"
    )


def test_declared_cutoffs_match_the_data(dataset):
    """The boundaries in configs/datasets.yaml are the ones actually realised on disk.

    Guards against the config drifting away from the artifacts it supposedly describes —
    the file would still look correct while the split no longer matched it.
    """
    name, splits = dataset
    cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[name]
    val_start = datetime.fromisoformat(cfg["val_start"])
    test_start = datetime.fromisoformat(cfg["test_start"])

    assert splits["train"]["timestamp"].max() < val_start
    assert splits["val"]["timestamp"].min() >= val_start
    assert splits["val"]["timestamp"].max() < test_start
    assert splits["test"]["timestamp"].min() >= test_start


# ------------------------------------------------------- the behaviour-window boundary

def test_no_history_click_at_or_after_its_impression(dataset):
    """Every history click strictly precedes the impression that uses it.

    This is the core anti-leakage property: a feature built from history must not see the
    future. Only checkable where history carries per-item timestamps (EB-NeRD); MIND ships
    none, and that is reported rather than passed vacuously.
    """
    name, splits = dataset
    if splits["train"]["history_timestamps"].dtype == pl.Null:
        pytest.skip(f"{name}: history has no per-item timestamps (structural guarantee only)")

    for split, df in splits.items():
        late = df.filter(pl.col("history_timestamps").list.max() >= pl.col("timestamp"))
        assert late.height == 0, (
            f"{name}/{split}: {late.height} impressions carry history at or after "
            f"their own impression time"
        )


def test_history_and_timestamps_are_aligned(dataset):
    """Per-item timestamps only mean anything if they pair 1:1 with the clicks.

    A length mismatch would make the leakage check above silently compare the wrong
    click to the wrong time.
    """
    name, splits = dataset
    if splits["train"]["history_timestamps"].dtype == pl.Null:
        pytest.skip(f"{name}: history has no per-item timestamps")

    for split, df in splits.items():
        bad = df.filter(
            pl.col("history").list.len() != pl.col("history_timestamps").list.len()
        )
        assert bad.height == 0, f"{name}/{split}: {bad.height} rows misalign history/timestamps"


# ------------------------------------------------------------------ label integrity

def test_clicked_is_a_subset_of_candidates(dataset):
    """A click outside the pool shown would be a label the system could never have found."""
    name, splits = dataset
    for split, df in splits.items():
        bad = df.filter(
            pl.col("clicked").list.set_difference(pl.col("candidates")).list.len() > 0
        )
        assert bad.height == 0, (
            f"{name}/{split}: {bad.height} impressions clicked outside their candidate pool"
        )


def test_every_id_resolves_and_none_is_empty(dataset):
    """Candidates must exist in the corpus, and no id may be the empty string.

    The empty-string case is not hypothetical: `"".split(" ")` is `[""]`, so a cold-start
    user with no history silently acquires a phantom one-item history and lands in the
    wrong evaluation slice.
    """
    name, splits = dataset
    known = set(pl.read_parquet(PROC / name / "articles.parquet")["article_id"])

    for split, df in splits.items():
        for col in ("candidates", "clicked", "history"):
            ids = set(df[col].explode().drop_nulls())
            assert "" not in ids, f"{name}/{split}.{col}: contains an empty article id"
            if col == "candidates":
                unknown = ids - known
                assert not unknown, (
                    f"{name}/{split}: {len(unknown)} candidates absent from articles.parquet"
                )


# ------------------------------------------------------------- serving availability

def test_no_scorer_reads_a_serving_unavailable_column():
    """The lifetime aggregates must not be referenced by any shipped scorer.

    They are carried in the corpus so the harness can quantify what they would buy
    (`eval/run.py`, deliberately). Any other module touching them would mean a number
    reported as servable was not.
    """
    forbidden = ("total_inviews", "total_pageviews", "total_read_time")
    allowed = {"eval/run.py"}

    # A grep-style test rather than a runtime one, deliberately. Leakage of this kind is a
    # question about which code is ALLOWED to touch a column, and that is a property of the
    # source, not of any single execution a runtime check might happen to miss.
    offenders = []
    for path in sorted((ROOT / "retrieval").glob("*.py")) + sorted((ROOT / "eval").glob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in allowed:
            continue
        text = path.read_text()
        offenders += [f"{rel}: {col}" for col in forbidden if col in text]

    assert not offenders, "serving-unavailable columns read outside eval/run.py: " + "; ".join(offenders)
