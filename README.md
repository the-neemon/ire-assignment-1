# IRE Assignment-1, Component-1 — lexical & semantic retrieval

Two-stage news recommendation on **EB-NeRD** (Danish, Ekstra Bladet) and **MIND** (English,
Microsoft), with a temporal data pipeline, BM25 and embedding candidate generation, and an
offline evaluation harness with bootstrap confidence intervals.

New to the project? Read `docs/WALKTHROUGH.md` first: it explains what the system does and why,
end to end, in plain English. `docs/NOTES.md` is the evidence trail (measured data facts and every
decision's justification), `deliverable/design_note_c1.pdf` is the write-up, and `results/` holds the
generated metric reports.

## Run it

```bash
make venv      # once: Python 3.11 venv + dependencies
make data      # Q1 on its own: raw archives -> feature store
make all       # download -> split -> retrieve -> evaluate
```

`make all` is idempotent: re-running skips completed downloads and rewrites the same bytes.
Individual stages: `make download`, `make split`, `make retrieve`, `make results`.
`make test` runs the anti-leakage checks against the built artifacts in seconds.

`make submissions` builds the two Codabench leaderboard files. It is deliberately outside
`make all`: the competitions score their own held-out test sets — EB-NeRD 13.5M impressions,
MIND-large 2.4M — not the temporal splits this repo evaluates on, so it downloads ~2.2 GB more
and takes ~13 min for EB-NeRD plus a one-off MIND encode.

**One manual step.** MIND is gated. The URL in every tutorial
(`mind201910small.blob.core.windows.net`) is dead — "Public access is not permitted on this
storage account" — and `msnews.github.io` now redirects to a HuggingFace mirror. Before the
first run, log in with `huggingface-cli login`, then open
<https://huggingface.co/datasets/yjw1029/MIND> and click *"Agree and access repository"*.
Access is automatic. EB-NeRD needs no auth.

## Layout

Source at the root, everything else grouped by what it is for.

```
Makefile                  one command rebuilds everything from raw files

configs/datasets.yaml     split cutoffs, language, stopwords, embedding source — per dataset
configs/stopwords_da.txt  Danish stopwords (bm25s ships none; measured worth +0.020 AUC)

pipeline/download.py      fetch + extract, idempotent
pipeline/split.py         temporal split -> normalised schema, with integrity assertions
pipeline/export_text.py   dump article text for off-machine (GPU) encoding
pipeline/submit.py        streaming scorer for the two Codabench leaderboards
retrieval/bm25.py         lexical scoring: re-rank track + full-corpus retrieval track
retrieval/embeddings.py   semantic scoring: same two tracks, same output shape
retrieval/fuse.py         per-pool z-normalised blend; alpha tuned on val only
eval/                     metrics, beyond-accuracy, slicing, bootstrap, runner
tests/test_leakage.py     no-future-click assertions against the built artifacts
notebooks/                article encoding on a Kaggle GPU

docs/WALKTHROUGH.md       how the system works and why, plain English — start here
docs/NOTES.md             measured facts, every decision, every ablation
docs/GLOSSARY.md          every term in the assignment, defined

deliverable/design_note_c1.tex  the write-up, LaTeX source (<=4 pages)
deliverable/design_note_c1.pdf  the graded deliverable; rebuild with `xelatex design_note_c1.tex`
deliverable/submissions/        the two Codabench zips

brief/Assignment1_v1.pdf  the authoritative assignment text
brief/SPEC.md             original build plan, historical

results/                  generated reports (markdown + json)
data/                     raw -> interim -> processed (gitignored)
```

## What it produces

`data/processed/<dataset>/` holds one schema for both datasets, so every downstream stage has a
single code path:

```
impressions_{train,val,test}.parquet
    impression_id, user_id, timestamp, candidates[], clicked[],
    history[], history_timestamps[]
articles.parquet
    article_id, title, abstract, body, category, entities, published_time,
    total_inviews, total_pageviews, total_read_time     <- serving-unavailable, eval only
```

Then per split: `bm25_*`, `emb_*`, `fused_*` (scores aligned to `candidates`) and
`retrieval_*`, `retrieval_emb_*` (full-corpus top-200).

## Correctness guarantees

`pipeline/split.py` asserts on every build, failing rather than warning:

- `train < val < test` strictly, by impression timestamp
- every history click strictly precedes its impression (per-item, EB-NeRD)
- `clicked` is a subset of `candidates`
- every candidate resolves to an article; no empty ids

Where a check is impossible it says so instead of passing vacuously — MIND's history carries no
per-item timestamps, so the harness reports that the guarantee there is structural rather than
verified. Outputs are byte-identical across runs.

`make test` re-checks the same properties from outside, reading only `data/processed/`. That is a
stronger claim than the build-time assertions: the build asserts what it *intended* to write, the
tests assert what is *actually on disk* and what every downstream stage therefore reads. One test
also fails if any module outside `eval/run.py` so much as mentions a serving-unavailable column.
