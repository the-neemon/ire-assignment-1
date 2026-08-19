# Assignment-1 Spec — News Recommendation on EB-NeRD & MIND

> **Historical document.** This was the build plan written before implementation started, from the
> initial assignment text. `Assignment1_v1.pdf` in this folder later superseded that text and is the
> authoritative brief. Kept to show what was planned; for what was actually built and why, see
> `docs/NOTES.md` and `docs/WALKTHROUGH.md`.

This spec operationalizes the brief into a concrete build plan, with **Component-1 as the
immediate, solo deliverable** and Component-2 scoped but deferred.

## 0. Big picture

One pipeline, exercised on **two datasets** (EB-NeRD and MIND), that ranks candidate articles in
an impression by click likelihood using three signal axes:

- **Lexical** — title/abstract/body text
- **Semantic** — article/text embeddings
- **Behavioural** — click history, session context, recency/decay

Built in two stages across two components:

| | Component-1 (now) | Component-2 (later) |
|---|---|---|
| Who | Solo | Groups of 2 |
| Due | 27 Aug (Quiz-1) | 10 Sep |
| Weight | 5% | 5% |
| Builds | Data pipeline, temporal split, candidate generation (BM25 + embeddings), offline eval harness | Behavioural features, re-ranker, baseline-then-beaten with ablation, serving/scale analysis |

Component-2 literally builds on top of the Component-1 repo, so decisions made now (schema, split
boundaries, candidate format) become the contract the future teammate inherits — keep them clean
and documented.

## 1. Datasets

| | EB-NeRD | MIND |
|---|---|---|
| Scale | ~2.7M users, 600M+ impressions, 120k+ articles | ~1M users, 160k+ articles, 15M+ impressions |
| Bundles | demo / small / large | MIND-small (fast iteration) / MIND-large |
| Content | title, abstract, body, **provided embeddings** | title, abstract, body, entity annotations (**no provided embeddings** — must generate) |
| Link | RecSys 2024 challenge, Ekstra Bladet | https://msnews.github.io/ |

**Recommendation:** develop end-to-end on `EB-NeRD demo` + `MIND-small` first (fast iteration, cheap
debugging), then re-run the exact same pipeline command on `EB-NeRD small` (and `large` only if time
and compute allow) to demonstrate scale-awareness for the design note. Never develop against `large`
first — the "one command rebuilds from raw files" requirement means scale-up should be a
config/flag change, not new code.

## 2. Component-1 deliverables (this is what's due 27 Aug)

### 2.1 Reproducible data pipeline
- Single command (e.g. `make rebuild` or `python -m pipeline.run --dataset ebnerd --scale demo`)
  that goes **download → clean → temporal split → feature store**, idempotently, from raw files.
- **Temporal train/val/test split — never random.** Pick a cutoff timestamp (or set of cutoffs) per
  dataset such that: train impressions strictly precede val impressions, which strictly precede test
  impressions. No impression, click, or feature may use information timestamped after its own
  impression time (this is also the anti-leakage requirement in §2.5).
- Small feature store: per-user, per-article, per-impression features materialized once, re-used by
  both candidate generation and (later) the re-ranker. Keep the schema stable — Component-2 depends
  on it.
- Config-driven scale selection (demo/small/large for EB-NeRD, small/large for MIND) so the same code
  path runs at any scale.

### 2.2 Candidate generation — lexical (BM25)
- Index title (+ abstract/body, ablate which fields help) per dataset.
- Tooling options: `rank_bm25` (pure Python, fine for demo/small) or Pyserini/Lucene (needed once you
  move to `large`/MIND-large — pure-Python BM25 will not scale).
- Given an impression's candidate list (MIND/EB-NeRD both ship a bounded candidate set per
  impression — you are **re-ranking their candidates with BM25 scores**, not retrieving from the
  full corpus, unless you choose to also demonstrate full-corpus retrieval for the design note).
- Output: BM25 score per (impression, candidate) pair, saved alongside the feature store.

### 2.3 Candidate generation — semantic (embeddings + ANN)
- EB-NeRD: use the **provided** article embeddings directly.
- MIND: no embeddings ship with it — generate them (e.g. `sentence-transformers` over
  title+abstract) once, cache to disk, and treat as a pipeline artifact (not recomputed on every run).
- Build an ANN index (FAISS flat/IVF is enough at demo/small scale) to score/narrow candidates to
  "a few hundred" as specified — even though most impressions already have small candidate pools,
  the ANN path should be demonstrated as it would work at full-corpus retrieval scale.
- Output: embedding similarity score per (impression, candidate) pair.

### 2.4 Offline evaluation harness
- **Accuracy metrics:** AUC, MRR, nDCG@5, nDCG@10 — computed per-impression then aggregated (this is
  the standard MIND/EB-NeRD leaderboard convention; match it so your numbers are checkable against
  the leaderboards).
- **Beyond-accuracy metrics:** diversity, novelty, coverage (define concretely in the design note —
  e.g. intra-list diversity via category/embedding distance, novelty via inverse popularity, coverage
  via fraction of catalog ever surfaced).
- **At least one slice**, e.g.:
  - cold-start users (short/empty click history) vs. warm users
  - head (popular) vs. tail (rarely-clicked) articles
- **Bootstrap confidence intervals** on the headline metrics (resample impressions with replacement,
  report e.g. 95% CI), not just point estimates.
- This harness must run over the outputs of both the BM25 path and the embedding path (and ideally a
  simple linear/weighted blend of the two) so Component-1 already shows a "two-stage" candidate
  generation system exercising both lexical and semantic axes, ready for Component-2 to slot a
  re-ranker on top.

### 2.5 Anti-gaming checks (organizer requirement — don't skip)
- Report metrics **with and without** any feature that would be unavailable at serving time (e.g. if
  you accidentally used post-impression signals).
- Enforce the behaviour-window boundary explicitly in code (a check/assertion, not just discipline).
- Add an automated test that asserts **no future-click leakage**: for a sample of impressions, verify
  every feature value used was computable strictly before that impression's timestamp.

### 2.6 Design note (≤4 pages, Component-1's half)
- What you built, choices made and alternatives considered (e.g. rank_bm25 vs Lucene, FAISS index
  type, split cutoff choice), observations from the offline eval, and where the current approach
  breaks at 10× scale (this last part is forward-looking — you're not solving it, just reasoning
  about it, e.g. pure-Python BM25 won't survive MIND-large without Lucene, in-memory FAISS flat index
  won't survive EB-NeRD-large without IVF/quantization).

## 3. Component-2 (deferred, scoped for context only)

Not started now. Builds on the Component-1 repo:
- Behavioural features from click-history/session (recency/decay features using the feature store
  from §2.1).
- Re-ranker (GBDT or small neural net) over BM25 + embedding + behavioural features.
- Reproduce the official/starter baseline, then beat it with one principled, ablated improvement;
  gains must ship a paired bootstrap 95% CI excluding zero.
- Serving/scale analysis: index memory, p99 retrieval latency, back-of-envelope cost/QPS at a target
  SLA.
- Second design note (≤4 pages).
- Grading also involves a signed component-ownership matrix and per-member viva — meaning your
  Component-1 code needs to stay something *you* can explain and modify live, not just something that
  runs.

## 4. Suggested repo layout

```
ass-1/
  SPEC.md
  Makefile                 # `make rebuild DATASET=ebnerd SCALE=demo`
  configs/
    ebnerd_demo.yaml
    ebnerd_small.yaml
    mind_small.yaml
  pipeline/
    download.py
    clean.py
    split.py                # temporal split, shared logic across datasets
    features.py             # feature store builder
  retrieval/
    bm25.py
    embeddings.py           # ANN index build + score
  eval/
    metrics.py              # AUC, MRR, nDCG@k
    beyond_accuracy.py       # diversity, novelty, coverage
    slicing.py
    bootstrap.py
    leakage_test.py          # anti-gaming / no-future-click-leakage checks
  data/                     # gitignored raw + processed artifacts
  notebooks/                # exploration only, not graded logic
  design_note_c1.pdf        # ≤4 pages
```

## 5. Milestones toward 27 Aug

Today is 1 Aug — 26 days out.

1. **Data pipeline + temporal split** working end-to-end on EB-NeRD demo and MIND-small (target: ~1 week).
2. **BM25 candidate scoring** wired into the feature store (~2-3 days).
3. **Embedding/ANN candidate scoring** — direct for EB-NeRD, generate-then-index for MIND (~3-4 days).
4. **Eval harness**: metrics + slicing + bootstrap CIs, validated against a leaderboard submission or
   sanity-checked baseline numbers (~1 week).
5. **Anti-gaming checks + leakage test** (~1-2 days) — do this before it's an afterthought; leakage
   bugs are easiest to introduce early and hardest to catch late.
6. **Scale up** to EB-NeRD small (and large if feasible) using the same command, note what breaks.
7. **Design note** (~2 days), buffer before 27 Aug.

## 6. Rubric mapping (full-assignment weights; Component-1 contributes to these, doesn't own them outright)

| Rubric item | Weight | Component-1's contribution |
|---|---|---|
| Reproducible pipeline + correct temporal evaluation | 30% | Fully owned by C1 (§2.1, §2.4) |
| Two-stage system, all three axes | 25% | C1 delivers stage 1 (lexical + semantic candidate gen); behavioural axis + re-ranker land in C2 |
| Baseline reproduced + ablated improvement | 20% | Owned by C2 |
| Serving/scale/cost analysis | 15% | Owned by C2 |
| Design-note clarity | 10% | C1 owns its half (§2.6) |

## 7. Open assumptions to confirm/adjust

- Language/stack assumed: Python, `rank_bm25`/Pyserini for BM25, `sentence-transformers` + FAISS for
  embeddings/ANN — swap freely, the spec doesn't depend on specific libraries.
- Assumed you're re-ranking the **provided candidate pools** per impression (standard MIND/EB-NeRD
  task framing) rather than retrieving from the full article corpus; flag if the course wants
  full-corpus retrieval instead.
- Bundle choice (demo/small vs. large) left as a scale-up decision in §5 step 6, adjust based on
  available compute/time.
