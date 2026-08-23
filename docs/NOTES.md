# Data notes — real schemas, timestamp ranges, chosen splits

Recorded from the actual downloaded files (not documentation). Everything downstream
(`split.py`, the feature store, the leakage test) is written against what is here.

Reproduce with `python -m pipeline.download`.

## Provenance

| dataset | source | note |
|---|---|---|
| EB-NeRD demo | `https://ebnerd-dataset.s3.eu-west-1.amazonaws.com/ebnerd_demo.zip` | public S3, no auth |
| EB-NeRD embeddings | same bucket, **`artifacts/` prefix** | the two the assignment names: `Ekstra_Bladet_word2vec.zip` (133 MB), `google_bert_base_multilingual_cased.zip` (344 MB) |
| MIND-small | HF dataset `yjw1029/MIND` | **gated** (`gated: auto`) — accept terms once at <https://huggingface.co/datasets/yjw1029/MIND> |

The `mind201910small.blob.core.windows.net` URLs in every tutorial and in the Microsoft
`recommenders` repo are **dead** — "Public access is not permitted on this storage account".
`msnews.github.io` now redirects to the HF mirror above. Don't waste time on the old URLs.

Extraction quirks: EB-NeRD zips carry `__MACOSX/` junk directories; MIND zips extract into a
nested duplicate folder (`MINDsmall_train/MINDsmall_train/`). Both are handled by pathing, not
cleanup.

## EB-NeRD demo

Danish. Timestamps are naive datetimes; the natural day boundary in the logs is **07:00**, not
midnight.

`articles.parquet` — 11,777 rows × 21 cols
```
article_id Int32 | title, subtitle, body String | published_time, last_modified_time Datetime
category Int16 | subcategory List(Int16) | category_str String | topics List(String)
ner_clusters, entity_groups List(String) | sentiment_score Float32, sentiment_label String
total_inviews, total_pageviews Int32, total_read_time Float32   <-- see leakage inventory
premium Boolean | article_type, url String | image_ids List(Int64)
```

`{train,validation}/behaviors.parquet` — 17 cols
```
impression_id UInt32 | user_id UInt32 | impression_time Datetime | session_id UInt32
article_ids_inview List(Int32)   <-- candidate pool
article_ids_clicked List(Int32)  <-- label (mean 1.01 per impression, max 7)
article_id Int32 | read_time, scroll_percentage Float32          <-- leakage
next_read_time, next_scroll_percentage Float32                   <-- leakage
device_type Int8 | is_sso_user, is_subscriber Boolean | gender, postcode, age Int8
```

`{train,validation}/history.parquet` — one row per user, parallel lists
```
user_id UInt32 | impression_time_fixed List(Datetime) | article_id_fixed List(Int32)
read_time_fixed List(Float32) | scroll_percentage_fixed List(Float32)
```

| | rows | impression_time range | users | history window |
|---|---|---|---|---|
| train | 24,724 | 2023-05-18 07:00:03 → 2023-05-25 06:59:52 | 1,590 | 2023-04-27 07:00:05 → 2023-05-18 06:59:51 |
| validation | 25,356 | 2023-05-25 07:00:15 → 2023-06-01 06:59:33 | 1,562 | 2023-05-04 07:00:11 → 2023-05-25 06:59:54 |

Each split ships **its own history file whose window ends exactly where its impressions begin** —
the behaviour-window boundary is given to us, cleanly, and is what the leakage test asserts.

Coverage checks (all clean): history covers 1,590/1,590 and 1,562/1,562 users; 0 inview articles
and 0 history articles missing from `articles.parquet`. Train∩validation users = 1,217.

Candidates per impression: mean 11.2, median 8, min 5, max 100. Distinct inview articles across
both splits: 3,729 (of 11,777 in the corpus).

### Provided article embeddings

The assignment names two, both 125,541 rows × 2 cols (`article_id Int32`, one `List(Float32)`):

| artifact | file | dim |
|---|---|---|
| `Ekstra_Bladet_word2vec` | `document_vector.parquet` | 300 |
| `google_bert_base_multilingual_cased` | `bert_base_multilingual_cased.parquet` | 768 |

Both cover **all 11,777** demo and **all 20,738** `ebnerd_small` articles (0 missing either way), and
being full-corpus artifacts they serve every bundle with no re-download. A third artifact in the same
folder, `Ekstra_Bladet_contrastive_vector` (768-d), is not named by the PDF but is what ultimately
ships; which encoder we use is settled by measurement, not preference. See "Choosing the EB-NeRD
encoder" and "Adopting contrastive_vector" below. This is the
semantic axis for EB-NeRD; nothing needs generating on that side. MIND has no equivalent and will need embeddings generated
(MiniLM on CPU over the 65,238-article union).

## MIND-small

English. `time` parses with `%m/%d/%Y %I:%M:%S %p`. Day boundary is midnight.

`behaviors.tsv` — headerless, 5 cols: `impression_id, user_id, time, history, impressions`.
`history` is a space-separated list of news IDs **with no timestamps**. `impressions` is
space-separated `N12345-1` / `N12345-0` (clicked / not).

`news.tsv` — headerless, 8 cols: `news_id, category, subcategory, title, abstract, url,
title_entities, abstract_entities` (entities are JSON strings with Wikidata IDs).

| | behaviors | time range | users | news.tsv |
|---|---|---|---|---|
| train | 156,965 | 2019-11-09 00:00:19 → 2019-11-14 23:59:13 | 50,000 | 51,282 |
| dev | 73,152 | 2019-11-15 00:00:01 → 2019-11-15 23:58:03 | 50,000 | 42,416 |

Train and dev are already **temporally disjoint** — dev is exactly the day after train ends.

Candidates per impression: mean 37.2, median 24, max 299 — substantially larger pools than EB-NeRD.
Cold-start (null history): 3,238/156,965 train (2.1%), 2,214/73,152 dev (3.0%).
History length: median 19, mean 32.6, max 558.

Article corpus: train and dev news files **differ** — union is **65,238** articles, with 13,956
dev-only. All dev candidates are covered by the union. **The retrieval index must be built over the
union**, or 21% of the corpus is unreachable at test time.

Text coverage: title 100%; abstract 94.8% (48,616/51,282 train). 17 categories, 264 subcategories —
category is the natural grouping for the diversity metric.

## Chosen temporal splits

Rule: train < val < test strictly, by impression timestamp. We adopt each dataset's own provided
boundary as the train/test boundary rather than inventing one, and carve val out of the earlier
block by time.

**EB-NeRD demo** (boundary 07:00)

| split | window | source | history source |
|---|---|---|---|
| train | `[2023-05-18 07:00, 2023-05-23 07:00)` (5 d) | provided `train/` | `train/history.parquet` |
| val | `[2023-05-23 07:00, 2023-05-25 07:00)` (2 d) | provided `train/` | `train/history.parquet` |
| test | `[2023-05-25 07:00, 2023-06-01 07:00)` (7 d) | provided `validation/` | `validation/history.parquet` |

**MIND-small** (boundary midnight)

| split | window | source |
|---|---|---|
| train | `[2019-11-09 00:00, 2019-11-13 00:00)` (4 d) | provided `train` |
| val | `[2019-11-13 00:00, 2019-11-15 00:00)` (2 d) | provided `train` |
| test | `[2019-11-15 00:00, 2019-11-16 00:00)` (1 d) | provided `dev` |

Realized counts (verified, ordering asserted):

| dataset | train | val | test |
|---|---|---|---|
| EB-NeRD demo | 17,852 (35.6%), 1,476 u | 6,872 (13.7%), 1,110 u | 25,356 (50.6%), 1,562 u |
| MIND-small | 95,071 (41.3%), 40,148 u | 61,894 (26.9%), 31,664 u | 73,152 (31.8%), 50,000 u |

EB-NeRD's test half being the largest block is a consequence of adopting the provided 7-day
`validation/` as test against a 5+2-day carve of `train/`. Kept deliberately: the test set is where
the bootstrap CIs are computed, and more test impressions means tighter intervals. The alternative
(train = all 7 provided train days, val/test = halves of provided validation) buys ~38% more
training data but makes test history up to 7 days stale by the end of the window; the current
arrangement keeps test history fresh at the test boundary.

Known conservatism, recorded deliberately: EB-NeRD val impressions use the train history window,
which ends 2023-05-18 07:00 — so history is up to 5 days stale by the end of val. This is *safe*
(strictly past-only) but pessimistic. Extending history with train-period clicks up to each
impression time is a feature-store improvement for C2, not something to silently do now.

## Observations from building the split

**EB-NeRD demo has no cold-start users at all** — 0 impressions with empty history across all three
splits, median history 258 clicks (max 1,459). The demo bundle is a sample of active users. MIND is
the opposite: median history 19, and 5,452 genuinely cold impressions (1.8% / 2.4% / 3.0% of
train / val / test).

Consequence for the eval harness: the required cold-vs-warm slice **cannot use "empty history" as
the cold definition on EB-NeRD** — it would select nothing. Use a history-length quantile (e.g.
bottom decile) as the shared definition across both datasets, and report the threshold. MIND can
additionally report the true zero-history slice.

**MIND-small ships no article body** — `news.tsv` carries title and abstract only (body requires
scraping the `url`). EB-NeRD has body for all 11,777. So the BM25 field ablation is
title / title+abstract on both, plus a body variant on EB-NeRD only.

Abstract coverage on the union corpus: 61,823/65,238 (94.8%).

**Reproducibility gotcha:** `polars.unique()` is hash-based and its row order varies between runs,
which made `mind_small/articles.parquet` non-deterministic byte-for-byte. Outputs are now sorted on
a unique key before writing (`article_id`, and `[timestamp, impression_id]` for impressions);
verified byte-identical across three consecutive runs.

## BM25 results (step 5)

Query = titles of the user's last 30 clicked articles. Documents = title + abstract.
Full run over both datasets and all six splits: **2m05s**, outputs byte-identical on re-run.

| dataset | split | AUC | MRR | recall@200 | random recall@200 |
|---|---|---|---|---|---|
| EB-NeRD demo | val | 0.5232 | 0.3455 | 0.0435 | 0.0170 |
| EB-NeRD demo | test | 0.5125 | 0.3273 | 0.0392 | 0.0170 |
| MIND-small | val | 0.5801 | 0.3169 | 0.0516 | 0.0031 |
| MIND-small | test | 0.5645 | 0.3076 | 0.0325 | 0.0031 |

**BM25 works on MIND and barely works on EB-NeRD.** MIND's AUC of 0.58 is a real lexical signal and
its retrieval track beats random by 10-17x. EB-NeRD sits at 0.51-0.52, close to random, and its
retrieval track beats random by only ~2.3x.

Before concluding that, two checks ruled out an implementation fault:

- *Oracle test* — setting the query to the clicked article's own title ranks it #1 in 300/300
  impressions, AUC 0.9990. So candidate scores are aligned to the right articles; the low numbers
  are a modelling result, not a plumbing bug.
- *History-length sweep* on EB-NeRD val: AUC 0.4967 / 0.4994 / 0.5018 / 0.5037 / 0.5035 / 0.5059 for
  the last 1 / 3 / 5 / 10 / 30 / 100 clicks. Flat — the long query is not diluting the signal.
  (Measured before the stopword fix below.)

**A defect this exposed:** bm25s ships no Danish stopword list, so EB-NeRD was originally indexed
with none. Queries built from ~30 concatenated Danish titles are then dominated by function words.
Supplying the standard Snowball Danish list (`configs/stopwords_da.txt`) moved val AUC
**0.5035 -> 0.5232**. Worth remembering as a general point: a missing stopword list is silent — it
degrades ranking without erroring.

Why EB-NeRD stays weak even after the fix (for the design note): its candidate pools are much
smaller (median 8-9 vs MIND's 23-26) and drawn from a tight recency window, so the candidates are
all plausible and topically close — there is little for lexical matching to separate. MIND's larger,
more heterogeneous pools leave more room.

Absolute retrieval recall is low on both (3-5% @200). Full-corpus BM25 alone is a weak candidate
generator for news: the EB-NeRD corpus spans 2000-2023 while impressions are from May 2023, and
`published_time <= impression_time` removes only *future* articles, not stale ones. Restricting the
retrievable corpus to a recency window is the obvious lever, and belongs with the behavioural
signals in C2 rather than here.

Cold-start users get a zero score vector and an **empty** retrieval list rather than an arbitrary
ranking — 5,452 MIND impressions, none on EB-NeRD.

## Embeddings and fusion (step 6)

Semantic axis: EB-NeRD uses the organisers' 300-d `Ekstra_Bladet_word2vec` document vectors,
chosen over `google_bert_base_multilingual_cased` by the ablation below; MIND is encoded with
`all-MiniLM-L6-v2` (384-d) over title+abstract — **11m16s on CPU** for 65,238 articles
(119 min CPU time, ~10.6x parallelism), cached so it runs once.

Fusion z-normalises both scores *within each candidate pool* and mixes them
`alpha*emb + (1-alpha)*bm25`, with alpha tuned on **val** and applied unchanged to test.

| dataset | split | scorer | AUC | MRR | nDCG@5 | nDCG@10 | recall@200 |
|---|---|---|---|---|---|---|---|
| EB-NeRD demo | val | bm25 | 0.5234 | 0.3456 | 0.3814 | 0.4627 | 0.0434 |
| | val | emb | 0.5140 | 0.3388 | 0.3704 | 0.4538 | 0.0327 |
| | val | fused (a=0.30) | **0.5288** | 0.3459 | 0.3845 | 0.4630 | — |
| | test | bm25 | 0.5125 | 0.3273 | 0.3591 | 0.4418 | 0.0390 |
| | test | emb | 0.5041 | 0.3147 | 0.3457 | 0.4317 | 0.0270 |
| | test | fused (a=0.30) | **0.5146** | 0.3260 | 0.3584 | 0.4424 | — |
| EB-NeRD small | val | bm25 | 0.5205 | 0.3418 | 0.3794 | 0.4607 | 0.0214 |
| | val | emb | 0.5098 | 0.3385 | 0.3708 | 0.4550 | 0.0153 |
| | val | fused (a=0.20) | **0.5236** | 0.3427 | 0.3810 | 0.4616 | — |
| | test | bm25 | 0.5107 | 0.3257 | 0.3577 | 0.4409 | 0.0247 |
| | test | emb | 0.5036 | 0.3175 | 0.3476 | 0.4344 | 0.0165 |
| | test | fused (a=0.20) | **0.5131** | 0.3254 | 0.3579 | 0.4414 | — |
| MIND-small | val | bm25 | 0.5801 | 0.3169 | 0.2892 | 0.3461 | 0.0516 |
| | val | emb | 0.6338 | 0.3411 | 0.3188 | 0.3776 | 0.0502 |
| | val | fused (a=0.80) | **0.6364** | 0.3449 | 0.3225 | 0.3811 | — |
| | test | bm25 | 0.5645 | 0.3076 | 0.2838 | 0.3450 | 0.0325 |
| | test | emb | 0.6339 | 0.3486 | 0.3315 | 0.3911 | 0.0353 |
| | test | **fused (a=0.80)** | **0.6353** | **0.3520** | **0.3343** | **0.3936** | — |

**Which axis wins is dataset-dependent, and the two datasets disagree.** On MIND the semantic axis
is decisively stronger (+0.069 AUC on test over BM25). On EB-NeRD, with the encoder the assignment
offers, it is the **weaker** of the two: `emb - bm25` is negative and significant on every EB-NeRD
split (small test −0.0072 [−0.0089, −0.0055]).

Fusion is what survives that disagreement. It beats the better single signal everywhere it is
significant, because lexical and semantic errors are only partly correlated — `fused - bm25` on
ebnerd_small is +0.0031 [+0.0020, +0.0043] on val and +0.0024 [+0.0017, +0.0030] on test. On
`ebnerd_demo` **test** the same comparison is +0.0020 [−0.0003, +0.0044] — the interval includes
zero, so at demo scale fusion's gain over BM25 alone is not established. It becomes established at
10x the impressions, which is an argument about statistical power, not about the method.

MIND's fused test AUC of 0.635 is within reach of the published neural baselines for MIND-small
(NAML/NRMS/LSTUR sit around 0.65-0.67) — from an entirely unsupervised, content-only system.

## Choosing the EB-NeRD encoder

The assignment names two pre-trained EB-NeRD encoders and marks them optional. Which to use is the
one modelling choice it leaves genuinely open, so it is settled by measurement. `make
encoder-ablation` runs the identical pipeline once per encoder — same splits, same BM25, same
fusion code, only the article vectors differ — so any difference is attributable to the encoder.

Selection is on **val**. Test is reported but never chosen on; picking the encoder by its test score
would tune a hyper-parameter on the number being reported, the same hygiene failure the temporal
split exists to prevent.

Semantic-only (`emb`) AUC, 95% bootstrap CI:

| encoder | dim | demo val | small val | fusion alpha (demo / small) |
|---|---|---|---|---|
| **`Ekstra_Bladet_word2vec`** | 300 | **0.5140** [0.5065, 0.5221] | **0.5098** [0.5073, 0.5124] | 0.30 / 0.20 |
| `google_bert_base_multilingual_cased` | 768 | 0.4877 [0.4797, 0.4954] | 0.4857 [0.4832, 0.4880] | 0.00 / 0.05 |

word2vec wins on both datasets and the intervals do not overlap, so the choice is not a coin toss.
Full reports for each are kept under `results/encoder_ablation/`.

**mBERT scores below 0.5 — worse than ranking at random.** That is not a bug; it is the expected
behaviour of raw, un-finetuned BERT vectors under cosine similarity. Their sentence representations
occupy a narrow cone in which almost everything looks similar, and the variation that remains tracks
surface properties (length, register) rather than topic. Mean-pooling 30 of them into a user vector
compounds it. Below 0.5 means the residue is mildly *anti*-correlated with clicks — plausibly
because the articles that look most "generic" to raw BERT are exactly the filler shown often and
clicked rarely. Fusion detects this without being told: alpha tunes to 0.00 on demo, i.e. the
mixer discards the semantic axis entirely.

Note the ordering is not the one dimensionality would predict — the 300-d model beats the 768-d one.
What matters is whether the training objective produced a space where cosine distance means topical
similarity. word2vec's does, weakly; raw mBERT's does not.

Recorded for completeness: an earlier build used `Ekstra_Bladet_contrastive_vector`, a third
artifact in the same official folder that the assignment does not name. It scored 0.5506
[0.5480, 0.5531] on ebnerd_small val — better than either named encoder, and the only EB-NeRD
configuration in which the semantic axis beats BM25. It was dropped to keep the system inside the
options the brief actually offers; the cost of that choice is ~0.041 AUC and is recorded here rather
than quietly absorbed. Its reports are kept under `results/encoder_ablation/contrastive_vector/`.

**Fusion helps on MIND and actively hurts on EB-NeRD** — and once the harness existed, the paired
bootstrap settled it rather than leaving it to judgement:

| comparison (test, AUC) | EB-NeRD demo | EB-NeRD small | MIND-small |
|---|---|---|---|
| emb − bm25 | +0.0293 ✓ | +0.0289 ✓ | +0.0693 ✓ |
| fused − emb | **−0.0035 ✓** | **−0.0017 ✓** | +0.0014 ✓ |

(✓ = 95% CI excludes zero.) On both EB-NeRD bundles the fusion difference is *significantly
negative*: alpha=0.70 wins on val and loses on test, so the alpha chosen on val did not generalise.
On MIND fusion wins on both, by a tiny but real margin that only 73k impressions could resolve.

**Report embeddings alone as the EB-NeRD headline, and fusion as the MIND headline.** There is no
honest reading in which fused is the better system on EB-NeRD.

## Scale-up to EB-NeRD small (step 6c)

`ebnerd_small` shares demo's collection window and 07:00 boundary exactly (verified, not assumed),
so the same cutoffs apply — but at ~10x the scale: 477,534 impressions over 15,143 users and 20,738
articles, against demo's 49,180 over 1,590 users.

**No code changed** — a config block was enough, which is the real test of the config-driven design.
Every `check_integrity` assertion passed unmodified. Runtimes: split 36s, BM25 1m44s,
embeddings 1m32s, fusion 1m10s, eval 3m26s.

| test AUC | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|
| EB-NeRD demo | 0.5125 | **0.5418** | 0.5384 | 0.5793 |
| EB-NeRD small | 0.5107 | **0.5397** | 0.5380 | 0.5797 |
| MIND-small | 0.5645 | 0.6339 | **0.6353** | n/a |

**Demo turned out to be representative.** Every system lands within 0.002 of its demo value at 10x
the users, and the fusion verdict is unchanged. The 10x data did buy much tighter intervals
(±0.0013 vs ±0.0040 on AUC), which is what made the small negative fusion effect resolvable.

## Serving-unavailable features (organiser requirement)

`fused+popularity` adds `log1p(total_inviews)` — an article's lifetime view count, a corpus-wide
aggregate computed over the whole collection period, so it embeds the future and cannot be computed
at serving time. Every other system uses only features available strictly before the impression.

| test, AUC | without | with popularity | difference |
|---|---|---|---|
| EB-NeRD demo | 0.5384 | 0.5793 | +0.0409 [+0.0380, +0.0437] ✓ |
| EB-NeRD small | 0.5380 | 0.5797 | +0.0417 [+0.0408, +0.0426] ✓ |

So the serving-unavailable feature is worth **~+0.041 AUC** — larger than the entire gain from
adding the semantic axis (+0.029). Any leaderboard comparison that quietly includes it is not
measuring the same system. MIND ships no equivalent aggregate, so the comparison is EB-NeRD only.

Retrieval recall@200 stays in the 3-5% band for both scorers and both datasets, with no consistent
winner (BM25 edges val, embeddings edge test). The full-corpus retrieval track is weak regardless of
scorer — see the corpus-staleness point in the BM25 section.

## Leakage inventory (drives the anti-gaming report)

**Never usable as features — strictly post-impression:**

- `next_read_time`, `next_scroll_percentage` (EB-NeRD behaviors) — the user's *next* action. A
  direct future leak; the name is the only warning you get.
- `read_time`, `scroll_percentage` (EB-NeRD behaviors) — engagement with the article clicked in
  *this* impression. Known only after the click being predicted.
- `article_id` (EB-NeRD behaviors) — the clicked article on the row; redundant with the label.

**Serving-unavailable — these are the "with and without" features the organizer requires:**

- `total_inviews`, `total_pageviews`, `total_read_time` (EB-NeRD articles) — lifetime aggregates
  computed over the entire collection period, i.e. they embed the future. Non-null for only
  7,506/11,777 articles. Metrics get reported both with and without them.

**Retrieval-side leak, easy to miss:** `published_time` in `articles.parquet` runs to
**2023-06-08**, past the test window end of 2023-06-01. Full-corpus retrieval must filter to
`published_time <= impression_time`, otherwise the index can return articles that did not yet exist.
This does not arise on the re-rank track, where the candidate pool is given.

**MIND limitation:** history carries no per-item timestamps, so a per-item "before impression time"
assertion is impossible there. The guarantee is structural (history precedes the log period) rather
than checkable. The leakage test asserts per-item on EB-NeRD and structural-only on MIND, and says
so rather than pretending to a check it cannot perform.

## Aligning to the released assignment PDF (Assignment1_v1.pdf)

The formal PDF (`brief/Assignment1_v1.pdf`) is the authoritative brief and superseded the earlier
plain-text version, which has been removed. Most requirements already matched; three changed the code.

**Q2.4 / Q3.4 — recall@K for K ∈ {50, 100, 200}.** The build stages had computed recall only at
K=200, printed it to the console, and never persisted it; `eval/run.py` did not open the
`retrieval_*.parquet` files at all, so recall appeared in none of the twelve reports. Now computed in
the harness with bootstrap CIs, per slice, plus a paired `emb - bm25` comparison at each K — which
is also the answer to Q3.5 ("which works better, and on which slices").

Recall is the *share of an impression's clicked articles* found in the top K, not the fraction of
impressions with at least one hit. The two coincide almost everywhere here — only 129 of 25,356
EB-NeRD demo test impressions have more than one click — but the PDF's wording ("how many
ground-truth clicked articles appear in the top-K candidates") asks for the former.

Cold-start impressions retrieve nothing and score 0 rather than being dropped. Excluding them would
report the recall of only the users the system could already serve.

**Q9 — "include a test asserting this."** The build-time assertions in `split.py` stay, but they only
fire while building. `tests/test_leakage.py` (19 tests, ~16s, `make test`) re-checks from outside,
reading only `data/processed/`. Two checks exist only there: that `datasets.yaml`'s declared cutoffs
still match the artifacts, and that no module outside `eval/run.py` mentions a serving-unavailable
column. Verified non-vacuous by injecting a future click into one row's history and confirming the
assertion fires — a suite that has never failed is not yet evidence of anything.

**Q1.4 — feature store must carry entities.** `_mind_news` had parsed `title_entities` /
`abstract_entities` and then dropped them in the `.select()`. Both datasets now normalise to
`entities: List(String)`: EB-NeRD from `ner_clusters` (74% on small, 86% on demo), MIND from the JSON `Label`
fields of title+abstract unioned (87%). `list.unique(maintain_order=True)` is deliberate — the
default is hash-ordered and would break the byte-identical rebuild.

Honest scope note: nothing scores on entities yet. They are carried because the feature store is a
schema contract, not because they improve a metric.

**Not addressed in code, needs a decision:** Q5 (mandatory Codabench submission to both leaderboards
+ screenshots in the design note; the RecSys track additionally needs `ebnerd_testset.zip`, 1.63 GB,
never downloaded), Q7.4 (AI usage log), and Q8 (the repo has no commits, and its git root is the
whole `semesters` tree rather than `ass-1`).

### Memory regression found and fixed while adding recall@K

The first implementation materialised the retrieval lists with `.to_list()`. At `ebnerd_small` that
is 245k impressions x 200 ids x 2 systems ≈ 98M Python strings; the harness was OOM-killed at 10 GB
RSS (confirmed in `dmesg`, not inferred from the exit code alone). Recomputing the intersection as a
Polars expression — so only one float per impression crosses into Python — cut peak RSS to 862 MB
and left the numbers identical to an independent numpy check. This is the §9 "memory is the first
wall" claim arriving early, and it is now a measurement rather than a prediction.

## Codabench submissions (Q5)

Both competitions' submission specs were fetched from the Codabench REST API
(`/api/competitions/<id>/`) — the web pages are a JS app and return nothing useful to a
plain fetch.

| | competition | inner file | evaluated on |
|---|---|---|---|
| MIND | 13967 | `prediction.txt` | MIND-large test, 2,370,727 impressions |
| EB-NeRD | 2469 | `predictions.txt` | `ebnerd_testset`, 13,536,710 impressions |

Same line format for both: `<impression_id> [r1,...,rn]`, where `ri` is the rank of the
i-th candidate *as listed in the test file*, 1 = best. Row order must match the test file.
The zip must contain the text file and nothing else.

**The leaderboards do not score demo or small.** EB-NeRD's guidelines are explicit —
"Codabench is only evaluating ebnerd_testset (1.5GB)" — and MIND's only open phase is
"Official Test", which is MIND-large. Development stays on EB-NeRD demo/small and
MIND-small as the PDF intends; the test sets are scored by inference only, since nothing
in this component is trained.

Operational limits worth knowing: EB-NeRD allows **5 submissions per day** and evaluation
"can take up to a few hours". That is why the output is validated offline (structure +
an independent float64 recomputation) rather than by trial upload.

### Why `pipeline/submit.py` exists instead of reusing retrieval/embeddings.py

The offline scorer materialises every impression at once. The EB-NeRD test set is 28x
`ebnerd_small` — 13.5M impressions, 205,925,868 candidate pairs — so it streams instead:
slices of 200k impressions, scored in 65,536-pair blocks, appended to the output and
discarded. Scoring *semantics* are unchanged (mean of last 30 history vectors,
L2-normalised, cosine), so the leaderboard entry and the offline report describe the same
system.

Polars slice pushdown reaches the parquet row groups, so `scan.slice(13_000_000, 200_000)`
costs the same as `slice(0, 200_000)` — measured 0.05s either way. That is what makes peak
memory flat in the number of impressions rather than linear.

Article ids are Int32 in EB-NeRD, so the lookup is an array indexed by id rather than a
dict of strings, keeping 206M candidate ids out of Python entirely.

### The `.to_list()` defect, found a third time

`np.vstack(series.to_list())` boxes every scalar into a Python float on the way through.
Measured on the 125,541 x 768 contrastive vectors: **peak 5.8 GB to build a 385 MB array**.
Replacing it with `explode().to_numpy().reshape(...)` cut the submitter's peak RSS from
7.0 GB to 5.9 GB and made it 33% faster, with byte-identical output.

The same pattern was in `retrieval/embeddings.py` (both the provided-vector and cached
branches); both are now `_unnest`, verified value-identical to the old path. This is the
third instance of the same defect (after the recall@K OOM), which is why §10 of the design
note names it as *the* scaling wall rather than one of several.

### MIND submission is embeddings-only, and that is a finding

The reported MIND system is `fused`, but the leaderboard entry uses embeddings alone.
BM25 here is `get_scores`, which returns a dense score over the whole corpus per distinct
query; at ~2M distinct histories x 120,961 articles that is ~10^11 operations and is not
practical. This is exactly the limitation §10 predicts — "BM25 scoring is O(corpus) per
distinct query ... a real inverted index with early termination becomes necessary" — now
confirmed by an attempt rather than argued from the code. Cost of the substitution is
known and small: fused − emb was +0.0014 AUC on mind_small test.

> **Superseded, 23 Aug.** "Not practical" was inferred from the operation count, never timed.
> Measured, it is ~1.6 h (1.6 ms/query, see "Can `fused` ship on the MIND leaderboard?" below).
> Expensive, not impossible. The paragraph above is kept as written so the correction is
> visible rather than edited away.

### MIND streaming needed a columnar file first

The first full MIND run was OOM-killed after 200k impressions. Cause: `stream_mind` read
`behaviors.tsv` whole — 2.37M rows, 1.45 GB in Arrow but **3.07 GB peak just to parse** —
and then did `.to_list()` on ~7.8M candidate strings per slice. It was never streaming;
only the EB-NeRD path was.

CSV has no slice pushdown, so the fix is a one-off conversion to parquet
(`_mind_parquet`) that also resolves article ids to integer row indices while still in
Polars, via `replace_strict` inside `list.eval`, written with `sink_parquet` so the
conversion itself never materialises. After that the MIND path is the same slice-pushdown
loop as EB-NeRD, and ~93M candidate strings never enter Python.

Peak RSS 4.2 GB -> 2.86 GB, and the first 20,000 output lines are byte-identical to the
pre-rewrite run, so the change is behaviour-preserving rather than merely smaller.

Worth recording as a process point: the diff against the earlier output initially looked
like a regression (179,959 differing lines). It was not — the file being compared against
was the *partial* output of the OOM-killed run, not the smoke test. The line-range notation
`20001,199959d20000` says lines 1-20000 were identical all along.

### Measured submission runs

| | impressions | wall | peak RSS | zip |
|---|---|---|---|---|
| EB-NeRD `ebnerd_testset` | 13,536,710 | 6m59s | 2.7 GB | 219 MB |
| MIND-large test | 2,370,727 | 6m05s | 1.3 GB | 103 MB |
| MIND-large encode (one-off) | 120,961 articles | 20m46s | 4.2 GB | cached 186 MB |

Peak RSS on the full 13.5M EB-NeRD run was the same as on a 20,000-impression smoke test,
which is the property that matters: memory flat in dataset size rather than linear in it.

Validation before upload (EB-NeRD allows 5 submissions/day, scored over hours), every
line of both files rather than a sample: line count equals source rows; zero `impression_id` out of
order; zero wrong candidate counts; zero rank lists that are not a permutation of 1..n;
each zip contains exactly its one expected text file. Separately, 40 random impressions
per dataset were re-ranked from scratch in float64 through an independent code path (dicts
rather than the lookup arrays the submitter uses) with zero mismatches.

## Dropping the self-chosen encoder (assignment fidelity)

The semantic axis originally used `Ekstra_Bladet_contrastive_vector`. It is an official EB-NeRD
artifact from the same `artifacts/` folder, but **the assignment PDF does not name it** — it names
`Ekstra_Bladet_word2vec` and `google_bert_base_multilingual_cased`, and marks the pair optional.
Choosing a third one was a decision the brief did not offer, so the system now uses the better of the
two it does, chosen by the val-only ablation in "Choosing the EB-NeRD encoder" above.

This costs accuracy and the cost is recorded rather than hidden: contrastive scored 0.5506 on
ebnerd_small val against word2vec's 0.5098. It was also the only EB-NeRD configuration where the
semantic axis beat BM25. Reporting a number produced by an encoder the brief never offered would
have been the worse trade.

**What the swap changed downstream**, all of it re-derived rather than edited by hand:

- every EB-NeRD row in the results table above, and all four `results/ebnerd_*.{md,json}`
- the fusion alphas: 0.70 -> 0.30 (demo) and 0.20 (small), because the semantic axis now deserves
  less weight
- three conclusions in `deliverable/DESIGN_NOTE.md` that reversed sign, rewritten rather than softened:
  §5 (BM25 now out-retrieves embeddings on EB-NeRD at every K), §6 (fusion is no longer rejected on
  EB-NeRD — it now wins where the comparison is powered), §11 (the submitted EB-NeRD system is now
  the *weakest* of the three measured, since embeddings-only lost to BM25)
- the EB-NeRD leaderboard zip, rebuilt from scratch; the superseded one was renamed
  `ebnerd_predictions.STALE-contrastive.zip` rather than deleted in place, so a half-finished
  rebuild could never be mistaken for a valid submission

`retrieval/embeddings.py` gained one flag, `--embeddings <parquet>`, to override the configured
vector file. That is the whole of the code change: because the encoder was already a config value
and `pipeline/submit.py` reads the same key, the leaderboard run cannot silently diverge from the
reported system. Verified the flag is a faithful no-op by pointing it at the config's own file and
confirming byte-identical output.

### The download was the slow part, not the compute

The two artifacts are 477 MB and this link sustained **34 kB/s** on a single stream — a 4-hour
download. Twelve parallel HTTP range requests to the same bucket sustained **1.06 MB/s**, 30x
faster, so the bottleneck was per-connection throttling rather than bandwidth. Fetched with ranged
`curl` into the path `pipeline/download.py` already expects, with each part's length checked against
its requested range and `unzip -t` over the assembled file, so a silently truncated range could not
survive into an extract. `download.py` itself is unchanged: it is the documented path, and it
short-circuits on the `.done` marker.

## Does text normalisation earn its place? (stemming ablation)

The assignment specifies nothing about tokenisation, stemming or stopwords — grep the PDF and
those words do not appear. So stemming was my choice, and until now an untested one. Three
variants on **val**, one thing changed at a time, everything else held fixed (same articles,
same queries, same stopword list, same BM25, same metric code as `eval/`):

| dataset | variant | vocab | AUC | recall@200 |
|---|---|---|---|---|
| ebnerd_small | none | 43,451 | 0.5202 [0.5176, 0.5226] | **0.0234** [0.0222, 0.0246] |
| | **stem** (ships) | 30,388 | **0.5205** [0.5177, 0.5230] | 0.0214 [0.0202, 0.0225] |
| | stem+split | 29,770 | 0.5165 [0.5137, 0.5192] | 0.0219 [0.0208, 0.0230] |
| mind_small | none | 60,914 | 0.5782 [0.5756, 0.5807] | **0.0384** [0.0370, 0.0397] |
| | **stem** (ships) | 44,264 | **0.5801** [0.5775, 0.5827] | 0.0361 [0.0347, 0.0373] |
| | stem+split | 41,650 | 0.5788 [0.5763, 0.5812] | 0.0323 [0.0310, 0.0335] |

Paired, `stem - none`:

| dataset | AUC | recall@200 |
|---|---|---|
| ebnerd_small | +0.0003 [-0.0014, +0.0019] **includes zero** | **-0.0020** [-0.0030, -0.0011] |
| mind_small | **+0.0019** [+0.0007, +0.0029] | **-0.0023** [-0.0031, -0.0015] |

**Stemming does not do what I assumed.** It helps re-ranking on English only, does nothing
measurable on Danish, and **significantly hurts full-corpus retrieval on both**. I had written
that stemming was the obvious standard choice; on the retrieval track that was wrong, and the
ablation is what caught it.

The mechanism is consistent across both datasets: stemming collapses distinct words into one
bucket, trading precision for recall of morphological variants. Ordering 8 candidates the log
already filtered, that trade pays on English. Picking 200 out of 20,738, the extra spurious
matches cost more than the variant-matching gains — the query is 30 concatenated titles and
already noisy, so making the index *less* discriminative is the wrong direction.

**Compound splitting was my idea, tested, and rejected.** Danish glues nouns together
(`fodboldkamp` = `fodbold` + `kamp`) and a rule-based stemmer cannot undo it, so I built a
greedy splitter from the corpus's own vocabulary, emitting parts alongside the original so a
wrong split could only add noise. It fired on 15% of tokens (7,451/50,328 Danish,
10,972/80,239 English) — so "no effect" is ruled out — and made things **worse**: -0.0040 AUC
on EB-NeRD and -0.0013 AUC / -0.0038 recall on MIND, all significant. Corpus-vocabulary
splitting produces too many false compounds; a real decompounder needs a proper Danish
lexicon, not word statistics. Recorded because a rejected idea with numbers is worth more
than an untried one.

**Kept stemming anyway**, deliberately: it is the right call for the reported headline metric
on MIND and neutral on EB-NeRD, and the effect sizes here (0.002-0.004 AUC) are an order of
magnitude below the encoder choice (0.04) and the serving-unavailable popularity feature
(0.05). Dropping it for Danish only is defensible on this evidence — per-language stopword
lists already exist, so per-language stemming would not strain the config — but it would buy
~0.002 recall and cost a full re-run of every EB-NeRD artifact and the leaderboard file.
Reproduce with `scratchpad/text_ablation.py`.

## Computing our own embeddings (Q3's second arm)

Q3 permits either "the provided article embeddings" **or** "compute your own using
BERT/XLM-RoBERTa". Having exhausted the provided arm, the second was worth testing — the
semantic axis was *losing* to BM25 on Danish, which is the weakest result in the report.

**Model: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`** — XLM-RoBERTa base
fine-tuned on paraphrase pairs. Chosen on the one property that has predicted every previous
result here: *was it trained so that cosine similarity means topical similarity?* Raw
mBERT was not, and scored below random. Encoded on a Kaggle T4 in ~4.5 min for all four
corpora (`notebooks/encode_articles.ipynb`); ~1,000-1,800 articles/s.

### EB-NeRD: adopted

Semantic-only AUC on **val**, ebnerd_small, everything else held fixed:

| encoder | dim | val AUC | vs BM25 (0.5205) |
|---|---|---|---|
| **xlmr (ours)** | 768 | **0.5309** [0.5282, 0.5336] | **wins** |
| contrastive_vector (not named by the brief) | 768 | 0.5506 [0.5480, 0.5531] | wins, but out of scope |
| word2vec (provided) | 300 | 0.5098 [0.5073, 0.5124] | loses |
| bert_base_multilingual_cased (provided) | 768 | 0.4857 [0.4832, 0.4880] | loses badly |

**`emb - bm25` flips sign: -0.0107 -> +0.0105 [+0.0069, +0.0140] on val, +0.0198
[+0.0182, +0.0215] on test.** The semantic axis now beats the lexical one on Danish, which it
never did with either provided encoder. Fusion's alpha moved 0.20 -> 0.60 (demo 0.30 -> 0.65)
without being told anything: the mixer independently reweighted toward meaning.

Best EB-NeRD test AUC: **0.5131 -> 0.5305, +0.0174** — roughly four times what stemming and
fusion were worth combined, and second only to the serving-unavailable popularity feature.

### MIND: rejected, and this one is the useful lesson

| encoder | val AUC | test AUC |
|---|---|---|
| **MiniLM (kept)** | **0.6338** [0.6312, 0.6362] | 0.6339 [0.6319, 0.6360] |
| xlmr | 0.6256 [0.6232, 0.6279] | **0.6364** [0.6343, 0.6385] |

**MiniLM wins on val; xlmr wins on test.** A genuine reversal with near-disjoint intervals, not
noise. Selection is on val by a rule fixed before looking, so MiniLM stays — and had the rule
been "pick the better test number", the choice would have gone the other way. This is the
cleanest demonstration in the whole project of why the selection split has to be decided in
advance; it cost us 0.0025 test AUC to obey it, and obeying it is the point.

The direction also makes sense: `all-MiniLM-L6-v2` is English-only, `paraphrase-multilingual`
spreads capacity over 50+ languages. A specialist beats a generalist on English, and the
generalist beats a 2013 word-vector model on Danish. So the encoders now differ per dataset —
each is the best *available* for its language, chosen the same way.

### What this does not fix

BM25 still out-retrieves embeddings on EB-NeRD at every K (recall@200 test: 0.0247 vs 0.0150).
The same encoder now wins re-ranking by +0.0198 and loses retrieval by ~40%, which sharpens
rather than weakens the two-track finding: ordering a pool the log already filtered and finding
200 items in a 20,738-article catalogue are different jobs.

Fusion also stopped paying on EB-NeRD test (`fused - emb` = -0.0014 [-0.0022, -0.0007],
significant), so the reported EB-NeRD headline is now **embeddings alone**. The alpha tuned on
val did not generalise — the same instability seen earlier with contrastive_vector, which
suggests EB-NeRD's optimal mix genuinely drifts over time rather than this being a one-off.

### Rebuilt artifacts

EB-NeRD leaderboard file regenerated with the new encoder: **33m28s, 5.9 GB peak** (768-d costs
~2.5x the 300-d run's 6m59s/2.7 GB). Validated on all 13,536,710 lines — line count, row order,
candidate counts, rank permutations, zip contents, CRC. `mind_prediction.zip` is untouched and
still valid: MIND kept MiniLM, and its cached test vectors are 384-d as expected.

## Which article fields to index (field ablation)

The last untested modelling choice. BM25 indexes `title + abstract` by default and always had;
`NOTES.md` had scoped a field ablation ("title / title+abstract on both, plus a body variant on
EB-NeRD only") and never run it, so the shipped setting was an assumption rather than a
measurement. EB-NeRD ships body text for all articles, which makes "why aren't you using it?"
an obvious question with, until now, no answer.

Run on **ebnerd_small val**, one thing changed at a time, everything else fixed (same queries,
same stopwords, same stemmer, same BM25, same metric code). Non-destructive: scored through
`retrieval.bm25`'s own functions without writing to `data/processed`, verified by checksumming
`bm25_val.parquet` before and after.

| variant | vocab | AUC | nDCG@10 | recall@200 |
|---|---|---|---|---|
| title | 15,132 | **0.5229** [0.5203, 0.5253] | **0.4628** [0.4607, 0.4649] | 0.0190 [0.0179, 0.0200] |
| **title+abstract** (ships) | 30,388 | 0.5205 [0.5177, 0.5230] | 0.4607 [0.4585, 0.4630] | **0.0214** [0.0202, 0.0225] |
| title+abstract+body | 123,867 | 0.5039 [0.5012, 0.5064] | 0.4477 [0.4456, 0.4498] | 0.0198 [0.0187, 0.0209] |

Paired against the shipped setting, all six differences significant:

| variant | AUC | nDCG@10 | recall@200 |
|---|---|---|---|
| title | +0.0025 [+0.0002, +0.0047] | +0.0021 [+0.0004, +0.0039] | -0.0024 [-0.0035, -0.0013] |
| +body | **-0.0166** [-0.0193, -0.0138] | -0.0130 [-0.0150, -0.0110] | -0.0016 [-0.0028, -0.0005] |

**Body hurts, and by a lot.** -0.0166 AUC is larger than everything fusion buys and comparable to
the entire encoder-switch gain (+0.0174). Vocabulary quadruples (30k -> 124k) and indexing slows
from 18s to 29s, so it is a significant cost for a significantly negative return. Not using the
body was right; it is now measured rather than assumed.

Mechanism: median body is 1,830 characters against a ~60-character title, so despite BM25's length
normalisation the title's topical terms get swamped by incidental body vocabulary, and the extra
text mostly buys spurious rare-word matches.

**The unexpected result is title-only beating the shipped title+abstract on re-ranking** (+0.0025
AUC) while losing on retrieval (-0.0024 recall@200), both significant. There is a likely cause,
and it is an asymmetry in the system rather than a property of the data: the BM25 **query is built
from titles only** (`build_queries` is passed `articles["title"]`), while documents are
title+abstract. So title-only documents are register-matched to the query, headline against
headline, and adding abstracts to one side only dilutes the terms the query is actually made of.

This is the same shape as the stemming result, now for the third time: **more text helps find
things in a large corpus and hurts ordering a small pool.** Ordering ~8 candidates the log already
filtered rewards a sharper, more discriminative index; picking 200 out of 20,738 rewards a broader
one. It sharpens the two-track finding rather than complicating it.

**Kept title+abstract anyway**, deliberately. It is the better setting for the retrieval track,
it is within 0.0025 AUC of the best re-ranking setting, and it is the only one of the three that
serves both tracks and both datasets from one index. Switching to title-only would buy ~0.0025
AUC on a track where EB-NeRD's headline system is embeddings rather than BM25, and cost recall on
the track where BM25 is the stronger retriever. Recorded rather than acted on.

Not tested, and worth stating: the title-vs-title+abstract question on **MIND**, where abstract
coverage is 94.8% and pools are ~3x larger, so the trade could land differently. And the embedding
side hardcodes title+abstract with no field flag, so testing body there means re-encoding on a GPU
rather than flipping a switch. Reproduce with `scratchpad/field_ablation.py`.

## Adopting contrastive_vector (final encoder decision, 19 Aug)

Reverses the earlier "Dropping the self-chosen encoder" section. That section removed
`Ekstra_Bladet_contrastive_vector` on the reading that the PDF names only `Ekstra_Bladet_word2vec`
and `google_bert_base_multilingual_cased`, and recorded the ~0.041 AUC the removal cost.

The reading was too narrow. Q3 offers "the provided article embeddings" or "compute your own using
BERT/XLM-RoBERTa". `contrastive_vector` is a provided article embedding, shipped in the same official
`artifacts/` folder as the other two; the PDF names those two as examples of that arm rather than as
its full extent. Adopting it is inside the brief, not outside it.

Semantic-only AUC on **val**, `ebnerd_small`, everything else fixed:

| encoder | arm | dim | val AUC |
|---|---|---|---|
| **contrastive_vector** (ships) | provided | 768 | **0.5506** [0.5480, 0.5531] |
| xlmr paraphrase (own) | own | 768 | 0.5309 [0.5282, 0.5336] |
| word2vec | provided | 300 | 0.5098 [0.5073, 0.5124] |
| bert_base_multilingual_cased | provided | 768 | 0.4857 [0.4832, 0.4880] |

Best EB-NeRD test AUC 0.5305 -> **0.5397** (+0.0092 over the xlmr build, +0.0290 over word2vec).

Reproduction note: the re-run's numbers match the archived `results/encoder_ablation/contrastive_vector/`
reports to four decimals, so the ablation artifacts and the shipped build agree.

### What the switch changed downstream

**The retrieval track flipped, and this is the substantive finding.** Under xlmr, BM25 out-retrieved
embeddings on EB-NeRD at every K. Under contrastive the winner depends on the split, significantly in
both directions:

| emb - bm25, recall@200 | val | test |
|---|---|---|
| ebnerd_small | **-0.0016** [-0.0030, -0.0002] ✓ | **+0.0030** [+0.0022, +0.0039] ✓ |
| ebnerd_demo | -0.0034 [-0.0093, +0.0027] | **+0.0071** [+0.0040, +0.0104] ✓ |

BM25 wins on val, embeddings win on test, same dataset and same code. Fusion shows the identical
pattern (`fused - emb`: +0.0022 ✓ on small val, -0.0017 ✓ on small test; alpha 0.70 on both bundles),
and it also appeared under xlmr, so it is a property of EB-NeRD rather than of one encoder or one
method. Plausible mechanism: val is a 2-day window against test's 7, the test block carries its own
later history window, and news relevance decays fast enough that the boundary is a distribution shift.

Design note §5 was rewritten around this. The old §5 claimed BM25 wins retrieval on EB-NeRD outright,
which is no longer true; the two-track finding survives as a difference of margin (+0.0289 AUC vs
+0.0030 recall@200, 10x) rather than of direction.

Unchanged: MIND (keeps MiniLM, untouched by this), the temporal split, BM25, and the harness.

### Two partial runs, and how they were caught

The re-run was killed twice mid-way by VSCode crashes, both times leaving mixed-encoder artifacts:
embeddings rewritten with contrastive while fusion and the reports were still xlmr-derived. Nothing
errored; `results/` simply described a system that never existed.

Caught by comparing artifact mtimes against `configs/datasets.yaml`'s mtime, since every score file
must postdate the config that produced it. That check is now the standard verification after any
encoder change, and it is worth more than a green test run: the tests all still passed in the
inconsistent state, because they assert leakage properties of the split, not agreement between stages.

`setsid` did not save the second attempt. What worked was running one stage per foreground call, so
each either completes or is visibly incomplete.

### Rebuilt leaderboard file (contrastive)

| | impressions | wall | peak RSS | zip |
|---|---|---|---|---|
| EB-NeRD `ebnerd_testset`, contrastive 768-d | 13,536,710 | **13m30s** | **5.64 GB** | 230.0 MB |

Faster than the xlmr build at the same dimensionality (33m28s / 5.9 GB) despite identical work, so
that earlier figure was measuring a loaded machine rather than the algorithm. Worth recording because
it is the kind of "benchmark" number that would have been quoted as a property of the code.

Peak RSS is unchanged from the xlmr run, which is the property that matters: memory is set by
`PAIR_BLOCK` and the vector table, not by the number of impressions.

Validated before upload, every line rather than a sample: 13,536,710 lines against the test file's
13,536,710 impressions and 205,925,868 candidate pairs; zero `impression_id` out of order; zero wrong
candidate counts; zero rank lists that are not a permutation of 1..n. Zip contains exactly
`predictions.txt` and nothing else. Separately, 40 random impressions were re-ranked from scratch in
float64 through an independent code path (dicts rather than the submitter's lookup arrays), with zero
mismatches.

### Rebuilt MIND leaderboard file (history_len=100, 23 Aug)

The MIND entry still used the pre-sweep `history_len=30`, submitted 5 Aug and scored 0.6460 AUC (comp.
13967, ID 892088). Rebuilt against the corrected config, no code change needed: `pipeline/submit.py`
already read `cfg["history_len"]`, so this was purely a rerun once the config carried 100.

| | impressions | wall | peak RSS | zip |
|---|---|---|---|---|
| MIND-large test, MiniLM 384-d, history_len=100 | 2,370,727 | **5m01s** | **1.27 GB** | 107.3 MB |

Validated the same way as the EB-NeRD rebuild: all 2,370,727 lines checked against the test file's
2,370,727 impressions and 93,115,001 candidate pairs, zero order/length/permutation failures, zip
contains exactly `prediction.txt`. 40 random impressions re-ranked independently in float64 with
`HISTORY_LEN` hardcoded to 100 rather than read from config, zero mismatches.

The superseded file is kept as `mind_prediction.STALE-history_len30-scored-0.6460.zip`, named with
the score it earned, same convention as the EB-NeRD rebuild.

Not yet done: uploading this and recording its score. Offline, `history_len=100` bought MIND `emb`
+0.0030 AUC (0.6339 -> 0.6369) at val/test scale; a similarly modest gain is the expectation here,
not a large jump, since nothing else about the system changed.

The superseded file is kept as `ebnerd_predictions.STALE-xlmr-scored-0.5336.zip` rather than deleted,
named with the score it earned so it cannot be confused with the current entry.

## MIND encoder ablation: mpnet / BGE / E5 vs shipped MiniLM (21 Aug)

Three retrieval-shaped alternatives to `all-MiniLM-L6-v2`, tested to see whether a bigger or
retrieval-tuned model beats it on MIND specifically, given size predicted nothing in the EB-NeRD
ablation. Encoded on Kaggle T4 (`notebooks/encode_articles.ipynb` §4): 65,238 articles, ~1.3-1.6
min each on GPU against an estimated 2.4h each on this machine's CPU (measured on a 500-article
sample of mpnet before deciding to move the job to Kaggle).

| model | dim | trained for |
|---|---|---|
| `all-MiniLM-L6-v2` (ships) | 384 | general sentence similarity |
| `all-mpnet-base-v2` | 768 | general sentence similarity, MiniLM's own family, larger |
| `BAAI/bge-base-en-v1.5` | 768 | retrieval, hard-negative mined |
| `intfloat/e5-base-v2` | 768 | retrieval; needs `"query: "`/`"passage: "` prefixes |

E5 has no literal query text in this architecture (a "query" is the mean of history article
vectors), so every article was prefixed uniformly `"passage: "` rather than exploiting the
query/passage asymmetry it was trained on. Noted as a real limitation on the E5 result, not
retroactively explaining it away.

Semantic-only AUC, `mind_small` val, same `history_len=100`, same protocol as every other encoder
ablation (`scratchpad/mind_encoder_ablation.py`, non-destructive, verified via checksum against
`data/processed/mind_small/emb_val.parquet` before/after):

| encoder | dim | val AUC | vs MiniLM (paired, 95% CI) |
|---|---|---|---|
| **MiniLM (shipped)** | 384 | **0.6356** [0.6331, 0.6380] | — |
| mpnet | 768 | 0.6344 | -0.0012 [-0.0029, +0.0004], not significant |
| e5 | 768 | 0.6067 | **-0.0289** [-0.0312, -0.0266], significant loss |
| bge | 768 | 0.5899 | **-0.0457** [-0.0481, -0.0432], significant loss |

**No candidate wins, and the AUC-vs-resource question has a clean answer: MiniLM dominates on
both axes at once.** It ties the best 768-d alternative (mpnet) on AUC while costing half the
FAISS index size and half the per-query cosine cost, and it beats the two retrieval-tuned models
outright and by a wide margin. There is no tradeoff to weigh; MiniLM was already the better
choice before resource cost even enters the argument.

**BGE's loss is the more surprising one.** E5's loss has a stated architectural reason (the
prefix mismatch); BGE has no equivalent excuse; it is a straightforward retrieval-tuned model
that lost decisively (-0.0457 AUC, the largest single-encoder gap measured anywhere in this
project) to a small general-purpose one on exactly the task it should suit. Consistent with the
EB-NeRD finding that neither model size nor stated training purpose reliably predicts performance
on mean-pooled cosine over short news text; only measurement does.

No config change: `mind_small` keeps `all-MiniLM-L6-v2`. Recorded because a rejected idea with
numbers is worth more than an untried one, same reasoning as the compound-splitting ablation.

## MIND field ablation and XLM-R re-check, and three new candidate ablations (23 Aug)

### XLM-R re-validated at history_len=100

The MiniLM-vs-XLM-R comparison (docs/NOTES.md, "Computing our own embeddings") was measured at the
pre-sweep `history_len=30`. Re-run at the shipped `history_len=100`:

| encoder | val AUC | vs MiniLM |
|---|---|---|
| **MiniLM (shipped)** | 0.6356 [0.6331, 0.6380] | - |
| xlmr | 0.6265 [0.6241, 0.6288] | -0.0090 [-0.0110, -0.0071], significant loss |

Same conclusion as before (MiniLM wins), same order of magnitude gap (-0.0090 vs the earlier -0.0082
at history_len=30). The choice was never actually in doubt at the new history_len; now confirmed
rather than assumed. No change.

### Field ablation on MIND (title vs title+abstract), previously untested

`scratchpad/field_ablation.py mind_small`, val, `history_len=100`, non-destructive:

| variant | vocab | AUC | nDCG@10 | recall@200 |
|---|---|---|---|---|
| **title** | 24,681 | **0.5864** [0.5840, 0.5887] | 0.3489 [0.3464, 0.3515] | **0.0388** [0.0374, 0.0402] |
| title+abstract (ships) | 44,264 | 0.5840 [0.5814, 0.5865] | 0.3494 [0.3468, 0.3522] | 0.0371 [0.0357, 0.0384] |

Paired, `title - title+abstract`: AUC +0.0024 [+0.0006, +0.0041] significant; nDCG@10 -0.0005
[-0.0020, +0.0011] not significant; recall@200 +0.0017 [+0.0007, +0.0028] significant.

**Different pattern from EB-NeRD.** There, title-only won re-ranking and *lost* retrieval (a real
trade). Here, title-only wins both accuracy metrics that moved, and the one that didn't move
(nDCG@10) shows no cost either way. No downside found. Candidate to ship: switch `mind_small`'s BM25
document fields to title-only. Not yet applied, pending the fields-are-per-dataset config plumbing
(currently `--fields` is a shared CLI flag, not a per-dataset config value like `history_len` is).

Mechanism, consistent with the stemming/field findings elsewhere: MIND abstracts run longer relative
to titles than EB-NeRD's, and the query is always title-only regardless of the document setting, so
adding abstract text to the *document* side while the *query* stays short-form dilutes the register
match on both tracks here, where on EB-NeRD's much smaller candidate pools the retrieval track still
benefited from the extra vocabulary.

### Entity overlap as a candidate signal — real, and worth adding

Jaccard overlap between a candidate's entities and the union of the user's last `history_len`
articles' entities (`scratchpad/entity_overlap_ablation.py`), MIND val, entities present for
57,054/65,238 articles:

Standalone: AUC **0.5370** [0.5344, 0.5394] (45,171/61,894 impressions had a nonzero score; the
rest have no entity overlap to measure). Weak alone, as expected, but real signal above 0.5.

Blended with the shipped `fused` score (z-normalised, `alpha*entity + (1-alpha)*fused`, swept on
val): best at alpha=0.15, **+0.0011 [+0.0008, +0.0015] AUC over fused alone, significant.**

**Measured again against `emb` alone, which is the number that actually matters**, since the
leaderboard submission is embeddings-only and will stay that way (no `fused` submission wanted):
best at alpha=0.20, **+0.0023 [+0.0018, +0.0027] AUC over emb alone, significant** — roughly twice
the gain it showed on `fused`.

That difference is itself the informative part: `fused` already contains BM25, and entity overlap is
partly lexical (shared named entities usually means shared tokens), so blending entities onto `fused`
double-counts signal that BM25 was already supplying. Against `emb` alone the entity axis is more
nearly orthogonal and contributes more. A reminder that "how much is signal X worth" has no answer
independent of what it is being added to.

Candidate to ship as a second signal alongside `emb`; not yet wired into the pipeline or verified on
test, this is a val-only finding by the same discipline every other choice here follows.

### Pooling: mean vs max-similarity — mean confirmed as the right choice

Alternative user representation: score a candidate by its best match to *any* single history item
(`max_h cosine(vector(h), candidate)`) rather than cosine to the mean-pooled centroid
(`scratchpad/max_pool_ablation.py`), MIND val:

| pooling | val AUC |
|---|---|
| **mean (shipped)** | **0.6356** [0.6331, 0.6380] |
| max-similarity | 0.6326 [0.6302, 0.6349] |

Paired: -0.0030 [-0.0048, -0.0011], significant loss. The centroid is the better representation
here; a user's single best-matching past article is a noisier signal than their average interest.
No change. Recorded because a rejected idea with numbers is worth more than an untried one.

### Cold-start fallback: popularity backoff — no significant effect, likely underpowered

Tested falling back to train-click popularity (log1p of train click count) for the 1,503 true
cold-start impressions in MIND val (2.4% of the split), against the shipped convention (all-zero
score, no ranking invented) (`scratchpad/cold_start_fallback_ablation.py`):

| | cold-slice AUC |
|---|---|
| zero-score (shipped) | 0.4929 [0.4766, 0.5081] |
| popularity fallback | 0.4978 [0.4816, 0.5138] |

Paired: +0.0049 [-0.0075, +0.0180], **not significant**. Both sit near 0.5 as expected (an all-tied
score ranks essentially at random). The interval is wide, 1,503 impressions is a small slice, so
this reads as underpowered rather than as proof popularity genuinely doesn't help; a larger cold
slice (MIND-large, or accumulating across more of MIND-small) would be needed to resolve it either
way. No change; recorded as inconclusive rather than negative.

### Can `fused` ship on the MIND leaderboard? The "not practical" claim was wrong

`NOTES.md` ("MIND submission is embeddings-only") and DESIGN_NOTE §10/§11 both assert BM25 cannot
back the MIND leaderboard entry: `get_scores` is dense over the corpus per distinct query, and at
~2M distinct MIND-large histories x 120,961 articles "that is ~10^11 operations and is not
practical". That claim was argued from an operation count and never timed.

Measured (`scratchpad/pool_restricted_bm25.py`, MIND val, single-threaded):

| | |
|---|---|
| dense `get_scores` | **1.6 ms/query** over 65,238 articles (1,957 queries in 3.1s) |
| extrapolated to MIND-large's 120,961-article corpus | ~2.9 ms/query |
| x ~2M distinct histories | **~1.6 hours** |

**~1.6 hours is slow, but it is not "not practical", and the earlier claim overstated the wall.**
10^11 *operations* is not 10^11 *seconds*; `bm25s` is sparse and vectorised, so the per-query cost
is milliseconds, not the seconds the operation count implies if read as scalar work. The honest
statement is that BM25 at this scale is expensive enough to be an annoyance (comparable to the
EB-NeRD submission's own 13m30s, but ~7x that), not that it is infeasible.

What that means for the submission: **`fused` is very likely shippable on MIND** for the +0.0012 AUC
it is worth offline, at a cost of roughly 1.6h of extra compute on top of the current 5m01s embedding
run. Not done here, it needs `pipeline/submit.py` to grow a BM25 path (it currently streams the
embedding scorer only) and that is a real code change, not a rerun. Recorded as a corrected estimate
and a live option rather than a closed door.

The pool-restriction idea specifically (score only the ~39 candidates per impression instead of all
120,961 articles) does **not** work as a shortcut with `bm25s`: its public API is `get_scores` over
the full corpus, with no per-document scoring entry point. That is a library limitation rather than
an arithmetic one; a real inverted index with early termination (WAND) would expose exactly that,
which is the §10 conclusion and still stands. The correction here is only to the *size* of the wall,
not to its existence or to the direction of the fix.

### Shipping the entity signal: val-selected, test-verified, wired into the submission

The entity finding above was val-only, so before shipping it I selected alpha on **val** and
reported it once on **test** with that alpha fixed (`scratchpad/entity_alpha_select.py`), the same
discipline used for the fusion weight and every encoder choice:

| | val | test |
|---|---|---|
| emb alone | 0.6356 | 0.6369 [0.6349, 0.6391] |
| emb + entity (alpha=0.20) | 0.6378 | **0.6391** [0.6370, 0.6413] |
| paired difference | +0.0023 | **+0.0022** [+0.0018, +0.0026], significant |

**It generalises**, val +0.0023 against test +0.0022, which is the part that matters and the part
EB-NeRD's fusion alpha conspicuously failed (§6: wins val, significantly loses test). Selecting on
val and finding the gain intact on test is the difference between a real improvement and a tuned one.

`entity_alpha: 0.20` now lives in `configs/datasets.yaml` under `mind_small` only. EB-NeRD has no
`entity_alpha`: its entities are `ner_clusters` with different coverage and the signal is untested
there, so it defaults to 0.0 and the EB-NeRD path is bit-for-bit unchanged.

`pipeline/submit.py` gained an entity path in `stream_mind`: `_mind_entity_sets` (same JSON parse as
`pipeline/split.py`) and `_zscore_blocks` (per-pool z-normalisation matching `retrieval/fuse.py`,
vectorised over the flat batch array via `np.bincount` rather than a Python loop per impression).
User entity sets are computed per *distinct history*, reusing the dedup `order` the user vectors
already build, so the added cost is per-history rather than per-impression.

Verified before the full run: a 20,000-impression smoke test re-checked against a fully independent
recomputation, different JSON parser (`json.loads` rather than Polars `json_decode`), float64
throughout, separate z-scoring, **zero mismatches over 40 random impressions**. That checks the
parse, the blend, the z-scoring scope and the ranking together, not just the arithmetic.

| MIND submission, entity-blended | impressions | wall | peak RSS | zip |
|---|---|---|---|---|
| MIND-large test, MiniLM 384-d, history_len=100, entity_alpha=0.20 | 2,370,727 | **4m38s** | **2.0 GB** | 107.3 MB |

Cost of the entity blend: +0.7 GB peak RSS over the emb-only build (1.27 GB), and no wall-clock
penalty at all (4m38s against 5m01s, inside run-to-run variance). All 2,370,727 lines validated for
order, candidate count and rank permutation.

The emb-only build is kept as `mind_prediction.EMBONLY-history_len100-unsubmitted.zip` (never
uploaded, so named for what it is rather than a score), alongside the scored
`mind_prediction.STALE-history_len30-scored-0.6460.zip`.

**Still embeddings-only in the lexical sense**: no BM25, no `fused`, per the decision not to ship a
fused submission. The entity signal is a second *content* axis blended onto embeddings, not the
lexical axis returning by another name.
