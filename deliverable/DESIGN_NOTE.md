# Component-1 Design Note — lexical & semantic retrieval on EB-NeRD and MIND

## 1. What was built

A config-driven pipeline from raw archives to metric reports in one command (`make data` for Q1's
feature store, `make all` for everything) across **EB-NeRD demo** (49k impressions/1,590 users),
**EB-NeRD small** (478k/15,143) and **MIND-small** (230k/50,000). Both normalise into one schema
(`impressions_*.parquet`: id, user, timestamp, candidates[], clicked[], history[]; `articles.parquet`:
id, title, abstract, body, category, entities[]), one code path rather than a Danish branch and an
English one. `entities` normalises two source shapes into one `List(String)` (74%/87% non-empty).

Three scorers run over that schema, **bm25**, **emb**, **fused**, on two tracks: **re-rank** (score the
pool the log actually showed; leaderboard-comparable) and **retrieval** (ignore the pool, pull the
top-200 from the whole corpus, the "candidate generation to a few hundred" the spec asks for). The
query for both is the user's last 30 clicked titles; the harness's own metrics are in §7.

## 2. Temporal split

Both datasets ship their own train/test boundary, so I adopted it as `test_start` rather than
inventing one, and carved `val` out of the earlier block by time (EB-NeRD small train/val/test:
168,522/64,365/244,647; MIND-small: 95,071/61,894/73,152 impressions). EB-NeRD's day boundary is
**07:00**, not midnight, a detail that only shows up in the data.

EB-NeRD ships a separate `history.parquet` per block whose window ends exactly where its impressions
begin, so the behaviour-window boundary is given rather than guessed (NOTES.md, §splits, for the
alternative considered and rejected).

**Enforcement, not discipline.** `split.py` asserts on every build, failing rather than warning:
strict `train < val < test`, history-precedes-impression, `clicked` a subset of `candidates`, every
candidate resolves. Where impossible it says so: MIND's history has no per-item timestamps, so the
guarantee there is structural rather than verified, not passed vacuously.

`tests/test_leakage.py` (`make test`, 19 tests, ~20s) re-checks the same properties from *outside*,
reading only `data/processed/`: the build asserts what it meant to write, the tests assert what is on
disk, plus two checks that exist only there (`datasets.yaml` cutoffs still match the artifacts; no
module outside `eval/run.py` mentions a serving-unavailable column). Verified non-vacuous by injecting
a future click and watching it fire.

## 3. Lexical axis

`bm25s` over title+abstract with a per-dataset Snowball stemmer (`rank_bm25` scores one query at a
time in pure Python, unusable at 65k documents; Pyserini/Lucene scales further but drags in a JVM).

**Stemming is not free, and not what I assumed.** The brief specifies no preprocessing, so this was my
choice. On val, `stem - none` is **+0.0019 [+0.0007, +0.0029] AUC on MIND, zero on EB-NeRD, and
significantly *negative* on recall@200 for both** (-0.0020, -0.0023): it trades precision for
variant-matching — worth it ordering ~8 candidates, harmful picking 200 from 20,738. Kept as right for
the headline metric, but a track-dependent trade. Danish compound splitting from corpus vocabulary
fired on 15% of tokens and made both **worse**: decompounding needs a lexicon, not statistics.

**The finding that mattered.** EB-NeRD first scored AUC **0.5035**, random. Rather than report that, I
checked whether it was my bug: an **oracle test** (query = the clicked article's own title) ranked it
#1 in 300/300 impressions at AUC 0.9990, and a history-length sweep was flat, ruling out misalignment
and query dilution. MIND worked at 0.58; that asymmetry located the cause: **bm25s ships no Danish
stopword list**, so thirty concatenated Danish titles were mostly function words. The Snowball list
moved EB-NeRD to **0.5232**. A missing stopword list is silent, it degrades without erroring.

## 4. Semantic axis

MIND encodes title+abstract with `all-MiniLM-L6-v2` (**11m16s**, cached once, 65,238-article union
across its two files). User vectors are the mean of last-30 history vectors, L2-normalised; scoring is
cosine with FAISS `IndexFlatIP` (exact at this scale; IVF/PQ deferred to 10× analysis).

**The encoder is a measurement, not a preference.** Q3 allows the provided article vectors *or* your
own from BERT/XLM-RoBERTa, so I ran the identical pipeline on each candidate: same splits, same BM25,
same fusion, only the article vectors differ. Selection is on **val**, since selecting on test tunes a
choice on the number being reported. Semantic-only AUC, `ebnerd_small` val, against BM25's 0.5205:

| encoder | arm | dim | val AUC | |
|---|---|---|---|---|
| **`Ekstra_Bladet_contrastive_vector`** (ships) | provided | 768 | **0.5506** [0.5480, 0.5531] | **beats BM25** |
| `paraphrase-multilingual-mpnet-base-v2` (XLM-R) | own | 768 | 0.5309 [0.5282, 0.5336] | beats BM25 |
| `Ekstra_Bladet_word2vec` | provided | 300 | 0.5098 [0.5073, 0.5124] | loses |
| `google_bert_base_multilingual_cased` | provided | 768 | 0.4857 [0.4832, 0.4880] | **below random** |

**On shipping `contrastive_vector`:** it is an official EB-NeRD artifact from the same `artifacts/`
folder as the other two, so it sits in Q3's "provided article embeddings" arm, word2vec and mBERT are
that arm's named examples, not its full extent. Strongest EB-NeRD encoder measured, by +0.0197 val AUC
over my own XLM-R, gap well outside both intervals.

One property predicts all four: **was the model trained so cosine distance means topical similarity?**
Contrastive training optimises exactly that and wins; XLM-R paraphrase fine-tuning approximates it and
comes second; word2vec (predict neighbouring words) does not; raw mBERT (fill in blanks) emphatically
does not, its vectors sitting in a narrow cone where everything looks alike. Size predicts nothing: the
300-d model beats one 768-d model. Fusion detects the mBERT failure unprompted, tuning alpha to 0.00 on
demo, discarding the semantic axis outright.

**MIND kept MiniLM, and that is the sharper lesson.** Against the same XLM-R, MiniLM wins on **val**
(0.6338 vs 0.6256) and *loses* on **test** (0.6339 vs 0.6364), a real reversal, near-disjoint intervals.
The rule was fixed before looking, so MiniLM stays; "take the better test number" would have flipped
it, costing 0.0025 test AUC to obey, the entire point of having a rule. An English specialist beats a
50-language generalist on English, while that generalist beats a 2013 word-vector model on Danish.

## 5. Candidate generation: recall@K, and a split-dependent winner

Recall@K over the **full catalogue**, not the pool the log showed, is what measures candidate
generation: the share of an impression's clicked articles found in the top K. Cold-start impressions
retrieve nothing and score 0 rather than being excluded, since a retriever that cannot serve a user has
failed for that user.

| recall@200 (small; demo tracked it within noise, §8) | bm25 | emb | emb − bm25 |
|---|---|---|---|
| EB-NeRD small · **val** | **0.0214** | 0.0198 | **−0.0016** [−0.0030, −0.0002] |
| EB-NeRD small · **test** | 0.0247 | **0.0277** | **+0.0030** [+0.0022, +0.0039] |
| MIND-small · test | 0.0220 | **0.0239** | +0.0019 [+0.0008, +0.0031] |

**On EB-NeRD the retrieval winner flips between val and test, both directions significant**: BM25
wins val, embeddings win test, same code, same K, a sign change with disjoint intervals, not noise.
MIND shows no such flip. §6 finds the identical pattern in the fusion weight, pointing at the dataset:
val is a 2-day window against test's 7, each with its own history window, so the lexical/semantic
relationship genuinely drifts, two weeks is a different news distribution.

**Re-ranking and retrieving stay different jobs, by margin now, not direction.** The same contrastive
vectors beat BM25 by **+0.0289** AUC ordering the pool and by only **+0.0030** recall@200 searching all
20,738 articles, a 10x gap for the same encoder and split, evidence for different signals per stage.
Absolute recall is low everywhere (2-5%), §8 explains why, a property of the corpus, not the retriever.

## 6. Fusion, an addition the brief did not ask for

Q3 asks only to *compare* lexical and semantic; this third system is mine. BM25 scores and cosines are on
different scales, and BM25's moves with query length, so both are z-normalised **within each candidate
pool** and mixed `alpha*emb + (1-alpha)*bm25`, alpha tuned on **val**, applied unchanged to test.

| AUC (small; demo tracked it within noise, §8) | bm25 | emb | fused | alpha | fused − emb |
|---|---|---|---|---|---|
| EB-NeRD small · **val** | 0.5205 | 0.5506 | **0.5528** | 0.70 | **+0.0022** [+0.0010, +0.0033] |
| EB-NeRD small · **test** | 0.5107 | **0.5397** | 0.5380 | 0.70 | **−0.0017** [−0.0023, −0.0011] |
| MIND-small · test | 0.5685 | 0.6369 | **0.6381** | 0.75 | **+0.0012** [+0.0005, +0.0018] |

**On EB-NeRD fusion wins on val and significantly loses on test, on both bundles**: the alpha chosen on
val does not generalise across the boundary. This is the same reversal §5 finds in retrieval, reached
through a different measurement, a property of EB-NeRD, not an artefact of either method.

Consequently **the reported EB-NeRD system is embeddings alone**, and only MIND ships fused. Fusion
still earns its place: it is the mechanism that *detected* the instability, and on MIND it is a real if
small win. Judged on val alone, the tempting shortcut, I would have shipped fusion on all three and
been wrong on two.

**`history_len` was shared across datasets and shouldn't have been.** A sweep on MIND val found the
constant (30) truncating a real tail: MIND's median history is 20, not EB-NeRD's 258, so 30 discarded
signal rather than noise. AUC rose significantly to 100 clicks (bm25 +0.0039, emb +0.0018) then
plateaued exactly there. EB-NeRD's own sweep (§3) was flat over the same range, so it stays at 30;
`history_len` is now per-dataset in config. This table reflects the corrected MIND value.

**A second MIND-only signal, entity overlap, ships alongside `emb`.** MIND's entities are clean and
Wikidata-linked; a candidate's Jaccard overlap with the user's recent-history entities, blended onto
`emb` (`alpha*entity + (1-alpha)*emb`), was selected on val (0.20) and checked once on test: **+0.0022
[+0.0018, +0.0026] AUC**, holding almost exactly (val +0.0023), unlike the fusion alpha above. Not
tried on EB-NeRD, its entities are a different extraction (`ner_clusters`) with different coverage.

## 7. Evaluation harness

Metrics are computed **per impression**: slicing is a mask over that vector, bootstrapping resamples
it over impressions, the approximately-independent unit. Comparisons use a **paired** bootstrap on
shared resamples, since two systems on the same impressions have correlated errors, an unpaired
comparison of independent intervals is far too conservative.

**Cold-start needed a defensible definition.** "Empty history" fails on EB-NeRD (zero such users,
median 258), so the harness uses a per-dataset bottom-decile threshold plus the true zero-history
slice where one exists; MIND's scores 0.5125 identically across systems, correctly, no history means
no ranking invented.

Beyond-accuracy over the top-10: category intra-list diversity, novelty as self-information against
*train* click shares, coverage, sobering at **5–21%** of the catalogue ever surfaced.

## 8. Observations

**Content signals are weak here, and that is the result, not a failure.** MIND reaches 0.6391 (§6),
within reach of published neural baselines for MIND-small (~0.65-0.67), unsupervised. EB-NeRD tops out
at 0.5397: pools are much smaller (median 8-9 vs MIND's 23-26) and drawn from a tight recency window,
so candidates are already plausible, little for content to separate.

**Simple behavioural features are not the shortcut they look like.** Train-click popularity scores
*below* random on EB-NeRD (0.459), the pool is already popularity-filtered.

**Demo was representative.** Every system landed within 0.002 of its demo value at 10× the users; the
extra data bought precision, CIs tightened from ±0.0040 to ±0.0013, deciding fusion.

**The retrieval track is weak regardless of scorer** (recall@200 of 2–5%): EB-NeRD's corpus spans
1998–2023 while impressions are one week in May 2023, and the publication filter removes only *future*
articles, not stale ones. A recency window on the retrievable corpus is the obvious C2 lever.

## 9. Anti-gaming and serving availability

`total_inviews`/`total_pageviews`/`total_read_time` are lifetime aggregates over the whole collection
period, embedding the future, and cannot be computed at serving time. Carried into the corpus **only**
so the harness can quantify them; no shipped scorer reads them. Test AUC without/with popularity:
EB-NeRD demo 0.5300 -> 0.5728, EB-NeRD small 0.5291 -> 0.5731 (+0.0440 [+0.0431, +0.0449]).

**One serving-unavailable feature is worth +0.044, more than twice the semantic axis (+0.0198, §6),
the largest legitimate win here**; any comparison quietly including it is not the same system.

Also enforced, not trusted: post-click engagement columns are dropped at the split, and retrieval
filters `published_time <= impression_time` (867 EB-NeRD articles postdate the test window).

## 10. Where it breaks at 10×, measured, not projected

The leaderboard submission made this section measured rather than hypothetical: Codabench scores
`ebnerd_testset` at **13.5M impressions, 205,925,868 candidate pairs, 28× `ebnerd_small`.**

**Memory is the wall, and it is one specific idiom.** Three separate times the break was `.to_list()`
pulling Arrow into boxed Python objects: `np.vstack(col.to_list())` peaks at **5.8 GB to build a 385 MB
array**, the same idiom OOM-killed the harness at 10 GB RSS adding recall@K. `explode().to_numpy()`
plus Polars set intersections fixed all three, byte-identically.

**Streaming works and costs little.** `pipeline/submit.py` scores in 200k-impression slices: peak RSS
stays **flat against dataset size, not linear**, in **13m30s** on the current contrastive-vector build
(33m28s at the same peak RSS under the earlier XLM-R build); MIND-large's 2.4M took 6m05s at 1.3 GB.
Slice pushdown reaches the parquet row groups, so an offset-13M slice costs the same as one at 0;
without it streaming would be O(n²). MIND needed a one-off TSV→parquet conversion first, CSV has no
such pushdown and OOM-killed the first attempt reading it whole (3.07 GB to parse).

**BM25 is expensive, and I first overstated by how much.** `get_scores` is dense over the whole
corpus per query; ~2M MIND-large histories x 120,961 articles I originally called impractical on the
~10¹¹ operation count alone. Timed: 1.6 ms/query, extrapolating to **~1.6 h**, roughly 7x the embedding
submission's runtime, slow but not a wall. Operation counts are not wall-clock for a sparse, vectorised
kernel; I should have measured first. The fix is unchanged: a dense per-query scorer is the wrong shape
here, and WAND-style early termination removes the cost. Projected at `ebnerd_large` (600M): FAISS flat
is O(N·d)/query, needing IVF-PQ with `nlist ~ sqrt(N)`.

## 11. Leaderboard submissions

Both competitions score held-out sets far larger than the splits above (`ebnerd_testset` 13.5M
impressions, MIND-large test 2.4M), streamed by `pipeline/submit.py` (§10), unchanged scoring
semantics. **Both entries are embeddings-only, not `fused`**: on EB-NeRD that *is* the reported system
(§6); on MIND, BM25 would cost ~1.6h on top of the 5min run (§10) for +0.0012 AUC, a deliberate trade
reported as a different system rather than letting `fused`'s number stand in for what was uploaded.

| | submission | AUC | status |
|---|---|---|---|
| EB-NeRD (RecSys 2024, comp. 2469) | 893893 | 0.5336 | superseded, XLM-R encoder |
| **EB-NeRD (final)** | **895220** | **0.5381** | current pipeline, `contrastive_vector` |
| MIND (comp. 13967) | 892088 | 0.6460 | superseded, `history_len=30`, embeddings-only |
| **MIND (final)** | **898179** | **0.6503** | current pipeline, `history_len=100` + entity blend (§6) |

**Each score reads against the offline number for the system that produced it.** 895220 (post-switch)
against offline `ebnerd_demo` `emb` test, 0.5418: leaderboard **−0.0037**, unremarkable, a larger
independent population regressing toward the mean. 898179 against offline `emb+entity` test, 0.6391:
leaderboard **+0.0112**, the reassuring direction. (An earlier draft mis-mapped 893893 to the wrong
encoder here; dropped rather than repeated.)

Both validated before upload: every line a correct-length rank permutation in test-file row order,
plus 40 re-ranked independently in float64. Excluded: 897967 (MIND, 0.5012), a `--limit` smoke test
that overwrote the real file pre-upload, scoring 2.37M candidates unranked; `submit.py` now isolates
smoke tests to their own path. **Screenshots:** *(893893, 895220, 892088, 898179)*
