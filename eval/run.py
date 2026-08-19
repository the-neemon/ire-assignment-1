"""The offline evaluation harness — the thing that decides what we are allowed to claim.

Produces, per dataset and split:
  * AUC / MRR / nDCG@5 / nDCG@10 with bootstrap 95% CIs
  * diversity / novelty / coverage
  * cold-vs-warm and head-vs-tail slices
  * paired-bootstrap comparisons between systems, which is what determines whether a
    difference is real rather than a rounding artefact
  * the with/without serving-unavailable-features report the organisers require

    python -m eval.run                       # every dataset, val + test
    python -m eval.run mind_small --splits test

Writes results/<dataset>_<split>.md and .json.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from eval import beyond_accuracy, bootstrap, metrics, slicing

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"

SYSTEMS = ["bm25", "emb", "fused"]
# Compared against `fused` to show what serving-unavailable popularity would buy.
LEAKY = "fused+popularity"

# The full-corpus retrieval track: candidate *generation* from the whole catalogue, scored
# by recall@K. Distinct from the tables above, which re-rank the pool the log already
# showed. `fused` has no retrieval track — fusion needs both scores over a shared pool.
RETRIEVAL_TRACKS = {"bm25": "retrieval_{split}.parquet", "emb": "retrieval_emb_{split}.parquet"}
RECALL_KS = (50, 100, 200)


def zscore(values: np.ndarray) -> np.ndarray:
    spread = values.std()
    return np.zeros_like(values) if spread < 1e-12 else (values - values.mean()) / spread


def load(name: str, split: str) -> pl.DataFrame:
    base = PROC / name
    df = pl.read_parquet(base / f"impressions_{split}.parquet")
    for system in SYSTEMS:
        df = df.join(pl.read_parquet(base / f"{system}_{split}.parquet"), on="impression_id")
    return df


def load_retrieval(name: str, split: str, impression_ids: pl.Series) -> dict[str, pl.Series]:
    """Full-corpus top-K lists per system, aligned to the impression order used everywhere else.

    Joining on impression_id rather than trusting row order: the retrieval files are written
    by a separate stage, and a silent misalignment here would score one user's retrieval
    against another user's clicks.

    Returned as Polars Series, never `.to_list()` — see `metrics.recall_at_k`.
    """
    base, order = PROC / name, pl.DataFrame({"impression_id": impression_ids})
    out = {}
    for system, pattern in RETRIEVAL_TRACKS.items():
        path = base / pattern.format(split=split)
        if path.exists():
            joined = order.join(pl.read_parquet(path), on="impression_id", how="left")
            # A missing row means that impression was never retrieved for; treat it as an
            # empty result (recall 0) rather than letting a null propagate into the metric.
            out[system] = joined["retrieved"].fill_null([])
    return out


def leaky_scores(df: pl.DataFrame, articles: pl.DataFrame) -> list[np.ndarray] | None:
    """`fused` plus lifetime popularity — deliberately NOT servable. None if unavailable."""
    # This system exists only to be reported against, not to be shipped. total_inviews is a
    # lifetime aggregate over the entire collection period, so for any given impression it
    # already knows how popular the article eventually became. That is exactly the kind of
    # feature the organisers want quantified rather than quietly used, so I build it here
    # (and nowhere else, which tests/test_leakage.py enforces) purely to price it.
    if articles["total_inviews"].null_count() == articles.height:
        return None
    inviews = dict(zip(articles["article_id"], articles["total_inviews"]))
    out = []
    for cand, fused in zip(df["candidates"].to_list(), df["fused"].to_list()):
        popularity = np.log1p(np.array([inviews.get(a) or 0 for a in cand], dtype=np.float64))
        out.append(zscore(np.asarray(fused, dtype=np.float64)) + zscore(popularity))
    return out


def evaluate(name: str, split: str, train_clicked: list, articles: pl.DataFrame) -> dict:
    df = load(name, split)
    candidates = df["candidates"].to_list()
    clicked = df["clicked"].to_list()
    labels = [
        np.fromiter((c in set(k) for c in cand), bool, len(cand))
        for cand, k in zip(candidates, clicked)
    ]

    scores = {s: [np.asarray(v, dtype=np.float64) for v in df[s].to_list()] for s in SYSTEMS}
    leaky = leaky_scores(df, articles)
    if leaky is not None:
        scores[LEAKY] = leaky

    values, keep = {}, None
    for system, score in scores.items():
        values[system], keep = metrics.per_impression(score, labels)

    # Slice masks are defined over all impressions, then restricted to the ones scored.
    # The `[keep]` below is what keeps every mask the same length as the metric vectors, so
    # a slice indexes the impressions it actually names and not an offset set of them.
    history_lengths = np.array([len(h) for h in df["history"].to_list()], dtype=np.float64)
    hist_slices, cold_threshold = slicing.by_history_length(history_lengths)
    counts = slicing.train_click_counts(train_clicked)
    pop_slices, head_threshold = slicing.by_article_popularity(clicked, counts)
    slices = {k: v[keep] for k, v in {**hist_slices, **pop_slices}.items()}

    info, unseen = beyond_accuracy.self_information_from(train_clicked)
    category_of = dict(zip(articles["article_id"], articles["category"]))

    report = {
        "dataset": name, "split": split,
        "impressions": df.height, "scored": int(keep.sum()),
        "cold_threshold_history_len": cold_threshold,
        "head_threshold_train_clicks": head_threshold,
        "overall": {}, "slices": {}, "beyond_accuracy": {}, "comparisons": {},
        "recall": {}, "recall_slices": {}, "recall_comparisons": {},
    }

    # --- full-corpus retrieval track: recall@K -------------------------------------
    retrieval = load_retrieval(name, split, df["impression_id"])
    recall = {
        system: metrics.recall_at_k(hits, df["clicked"], RECALL_KS, keep)
        for system, hits in retrieval.items()
    }
    for system, by_k in recall.items():
        report["recall"][system] = {
            f"recall@{k}": dict(zip(("mean", "lo", "hi"), bootstrap.ci(vals)))
            for k, vals in by_k.items()
        }
    # Which retriever wins, and on which slices — the lexical-vs-semantic question.
    if {"bm25", "emb"} <= set(recall):
        for k in RECALL_KS:
            mean, lo, hi, sig = bootstrap.paired(recall["emb"][k], recall["bm25"][k])
            report["recall_comparisons"][f"emb - bm25 (recall@{k})"] = {
                "mean": mean, "lo": lo, "hi": hi, "significant": sig
            }
        top_k = max(RECALL_KS)
        for slice_name, mask in slices.items():
            if mask.sum() < 30:
                continue
            # Paired within the slice, because which retriever wins is not the same
            # everywhere: the overall verdict reverses on head articles.
            mean, lo, hi, sig = bootstrap.paired(
                recall["emb"][top_k][mask], recall["bm25"][top_k][mask]
            )
            report["recall_slices"][slice_name] = {
                "n": int(mask.sum()),
                **{s: dict(zip(("mean", "lo", "hi"), bootstrap.ci(recall[s][top_k][mask])))
                   for s in recall},
                "emb - bm25": {"mean": mean, "lo": lo, "hi": hi, "significant": sig},
            }

    for system in scores:
        report["overall"][system] = {
            metric: dict(zip(("mean", "lo", "hi"), bootstrap.ci(vals)))
            for metric, vals in values[system].items()
        }
        extra = beyond_accuracy.evaluate(
            candidates, scores[system], category_of, info, unseen, articles.height
        )
        report["beyond_accuracy"][system] = {
            "diversity": float(extra["diversity"].mean()),
            "novelty": float(extra["novelty"].mean()),
            "coverage": float(extra["coverage"]),
        }

    for slice_name, mask in slices.items():
        # Below ~30 impressions the bootstrap interval is so wide it says nothing, so I omit
        # the slice rather than print a number that invites over-reading.
        if mask.sum() < 30:      # too few impressions for a meaningful interval
            continue
        report["slices"][slice_name] = {
            "n": int(mask.sum()),
            **{
                system: dict(zip(("mean", "lo", "hi"), bootstrap.ci(values[system]["auc"][mask])))
                for system in scores
            },
        }

    # The comparisons that answer the assignment's questions: does semantic beat lexical,
    # does fusing beat either alone, and what would the unservable feature have bought.
    pairs = [("emb", "bm25"), ("fused", "emb"), ("fused", "bm25")]
    if leaky is not None:
        pairs.append((LEAKY, "fused"))
    for a, b in pairs:
        for metric in ("auc", "ndcg@10"):
            mean, lo, hi, sig = bootstrap.paired(values[a][metric], values[b][metric])
            report["comparisons"][f"{a} - {b} ({metric})"] = {
                "mean": mean, "lo": lo, "hi": hi, "significant": sig
            }
    return report


def render(report: dict) -> str:
    systems = list(report["overall"])
    out = [f"# {report['dataset']} — {report['split']}", ""]
    out.append(f"{report['impressions']:,} impressions, {report['scored']:,} scored "
               f"(the rest are all-clicked or none-clicked and carry no ranking signal).")
    out.append("")
    out.append("## Accuracy (mean [95% bootstrap CI])")
    out.append("")
    out.append("| system | AUC | MRR | nDCG@5 | nDCG@10 |")
    out.append("|---|---|---|---|---|")
    for s in systems:
        row = [bootstrap.fmt(**report["overall"][s][m]) for m in ("auc", "mrr", "ndcg@5", "ndcg@10")]
        out.append(f"| {s} | " + " | ".join(row) + " |")

    out += ["", "## Beyond accuracy (top-10)", "",
            "| system | diversity | novelty | coverage |", "|---|---|---|---|"]
    for s in systems:
        b = report["beyond_accuracy"][s]
        out.append(f"| {s} | {b['diversity']:.4f} | {b['novelty']:.4f} | {b['coverage']:.4f} |")

    if report["slices"]:
        out += ["", "## AUC by slice", "",
                f"cold = history length <= {report['cold_threshold_history_len']:.0f}; "
                f"head = clicked article with >= {report['head_threshold_train_clicks']:.0f} train clicks",
                "", "| slice | n | " + " | ".join(systems) + " |",
                "|---" * (len(systems) + 2) + "|"]
        for name, data in report["slices"].items():
            cells = [bootstrap.fmt(**data[s]) for s in systems]
            out.append(f"| {name} | {data['n']:,} | " + " | ".join(cells) + " |")

    if report.get("recall"):
        retrievers = list(report["recall"])
        out += ["", "## Candidate generation — recall@K (full-corpus retrieval)", "",
                "Share of an impression's clicked articles found in the top K drawn from the "
                "whole catalogue, not the pool the log showed. Cold-start impressions retrieve "
                "nothing and score 0 rather than being excluded.", "",
                "| system | " + " | ".join(f"recall@{k}" for k in RECALL_KS) + " |",
                "|---" * (len(RECALL_KS) + 1) + "|"]
        for s in retrievers:
            cells = [bootstrap.fmt(**report["recall"][s][f"recall@{k}"]) for k in RECALL_KS]
            out.append(f"| {s} | " + " | ".join(cells) + " |")

        if report.get("recall_slices"):
            out += ["", f"### recall@{max(RECALL_KS)} by slice", "",
                    "Which retriever wins is not the same on every slice — see `emb - bm25`, "
                    "paired within the slice.", "",
                    "| slice | n | " + " | ".join(retrievers) + " | emb - bm25 | significant |",
                    "|---" * (len(retrievers) + 4) + "|"]
            for slice_name, data in report["recall_slices"].items():
                cells = [bootstrap.fmt(**data[s]) for s in retrievers]
                d = data["emb - bm25"]
                out.append(
                    f"| {slice_name} | {data['n']:,} | " + " | ".join(cells) +
                    f" | {d['mean']:+.4f} [{d['lo']:+.4f}, {d['hi']:+.4f}] |"
                    f" {'yes' if d['significant'] else 'no'} |"
                )

    out += ["", "## Paired bootstrap comparisons", "",
            "A difference counts only if its 95% CI excludes zero.", "",
            "| comparison | difference | significant |", "|---|---|---|"]
    for name, c in {**report["comparisons"], **report.get("recall_comparisons", {})}.items():
        out.append(f"| {name} | {c['mean']:+.4f} [{c['lo']:+.4f}, {c['hi']:+.4f}] | "
                   f"{'yes' if c['significant'] else 'no'} |")

    if any(s == LEAKY for s in systems):
        out += ["", "## Serving-availability",
                "",
                f"`{LEAKY}` adds article lifetime popularity (`total_inviews`), a corpus-wide "
                "aggregate that embeds the future and is unavailable at serving time. Every other "
                "row uses only features computable strictly before the impression. The paired "
                f"comparison `{LEAKY} - fused` above is the cost of honesty."]
    return "\n".join(out) + "\n"


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="*", default=list(config))
    parser.add_argument("--splits", nargs="+", default=["val", "test"])
    args = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    for name in args.datasets:
        articles = pl.read_parquet(PROC / name / "articles.parquet")
        train_clicked = pl.read_parquet(PROC / name / "impressions_train.parquet")["clicked"].to_list()
        for split in args.splits:
            print(f"{name} {split} ...", flush=True)
            report = evaluate(name, split, train_clicked, articles)
            (RESULTS / f"{name}_{split}.json").write_text(json.dumps(report, indent=2))
            (RESULTS / f"{name}_{split}.md").write_text(render(report))
            print(f"  -> results/{name}_{split}.md")


if __name__ == "__main__":
    main()
