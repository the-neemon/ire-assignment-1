# Walkthrough: what this system actually does, and why

Written to be read start to finish, in plain English, assuming you know nothing.
`GLOSSARY.md` defines individual words; this explains how they fit together.

Every number here comes from `NOTES.md` or `results/`. Nothing is invented.

---

## 1. The task, in one sentence

A person is shown a list of news articles. Some they click, most they don't.
**Your job: put that list in the right order, clicked ones at the top.**

That's it. You are not choosing what to show. You are not writing headlines. You are given
a list somebody was actually shown, and you re-order it.

## 2. The single most important thing to understand

**Nothing in Component-1 is trained. There is no model with learned weights. There is no
loss function, no gradient descent, no epochs.**

This is the thing you most need to be able to say out loud, because "what did you train on"
is the obvious viva question and the honest answer is "nothing, deliberately".

When you asked "what do we train on, how do we train", the answer is that the question
doesn't apply yet. Component-1 is a **retrieval** system, not a **learning** system. It works
by measuring similarity:

> "This person recently read articles A, B and C. Which of the candidates in front of me is
> most similar to A, B and C?"

Similarity is computed two ways (word overlap, and meaning), and those are combined. No
training data is consumed to fit parameters, because there are no parameters to fit.

Component-2 (the pair project) is where a trained re-ranker arrives. That's why the brief
splits them: C1 builds the measuring apparatus and the honest evaluation, C2 adds learning
on top.

**Then what is the train split for?** Two things only, both of them bookkeeping rather than
learning:

1. **Popularity counts** for the evaluation, so "is this a popular or an obscure article?"
   is decided using only the past (`eval/slicing.py`, `eval/beyond_accuracy.py`).
2. **A held-out region of time** that val and test must come after, which is what makes the
   temporal ordering meaningful at all.

The one number that is actually *tuned* is the fusion weight `alpha`, a single value between
0 and 1, and it is tuned on **val**, not train. More on that in §9.

---

## 3. The atom of the data: an impression

Everything is built from one record type. An **impression** is one moment:

```
who:        user U73
when:       2023-05-24 08:14:02
shown:      [A991, A102, A448, A771, A053, A882, A310, A667]   <- candidates
clicked:    [A448]                                              <- the label
their past: [A031, A559, A004, ... ]                            <- click history
```

Four parts, and each one has a job:

- **candidates** are what you must order.
- **clicked** is the answer key. Usually exactly one article (EB-NeRD averages 1.01 clicks
  per impression, max 7).
- **history** is your only clue about this person. It is the *input* to your system.
- **timestamp** is what makes the whole assignment honest, because it lets you prove your
  history really came from before the moment you're predicting.

`pipeline/split.py` converts both datasets into exactly this shape, so everything downstream
has one code path. That normalisation is why the same BM25 code runs on Danish and English
without knowing which it's looking at.

---

## 4. The two datasets, and how they differ

Both are real logs from real news sites. They differ in ways that turn out to matter a lot.

### EB-NeRD (Ekstra Bladet, Danish tabloid)

Used at `demo` scale (11,777 articles, ~49k impressions, 1,590 users) and `small`
(20,738 articles, 477,534 impressions, 15,143 users).

- Language: **Danish**
- Ships article **body text**, not just title and abstract
- Ships **publication dates**, which matter for the retrieval track (§7)
- Ships **pre-made article embeddings** (§8)
- Ships **lifetime view counts**, which are a leakage trap (§11)
- History has **per-item timestamps**, so you can check leakage click by click
- **No cold-start users at all.** Zero impressions with empty history. Median history is
  258 clicks. This bundle is a sample of *active* users.
- Candidate pools are **small**: mean 11.2, median 8

### MIND (Microsoft News, English)

Used at `small` scale: 65,238 articles (train and dev news files differ, so you must use
their union), 156,965 + 73,152 impressions, 50,000 users.

- Language: **English**
- **No body text.** Title and abstract only (abstract present for 94.8%)
- **No publication dates**
- **No pre-made embeddings.** You generate them yourself
- History is a bare list of article IDs with **no timestamps**
- **Has real cold-start users**: 5,452 impressions with empty history
- Candidate pools are **larger**: mean 37.2, median 24, max 299

### Why the differences matter

These aren't trivia, they're the reason your results look the way they do:

| difference | consequence |
|---|---|
| MIND has bigger, more varied pools | more room for a scorer to separate good from bad, so scores are higher there |
| EB-NeRD pools are small and topically tight | candidates are all plausible, little to distinguish, AUC hovers near 0.51 |
| MIND history has no timestamps | the per-click leakage assertion is *impossible* there; the guarantee is structural only |
| EB-NeRD has no cold-start users | the "cold vs warm" slice can't use "empty history" as its definition, so a bottom-decile cutoff is used on both |
| MIND has no publication dates | full-corpus retrieval can't filter out not-yet-published articles there |

That last one and the timestamp one are the sort of thing a viva examiner loves, because the
honest answer is "I couldn't, and I said so rather than faking it".

---

## 5. The temporal split: what train, val and test are actually for

**The rule: everything is divided by time. Never randomly.**

Why: news recommendation predicts the future. If you shuffle rows randomly, some of your
"training" data is from *after* your "test" data, so you'd be using knowledge of the future
to predict the past. Your score would look great and mean nothing. A real system serving
live traffic has only the past.

Both datasets already ship their own two blocks. Rather than invent boundaries, the split
adopts theirs and carves validation out of the earlier block:

**EB-NeRD demo** (the day boundary in these logs is 07:00, not midnight):

| split | window | comes from |
|---|---|---|
| train | 18 May 07:00 to 23 May 07:00 (5 days) | provided `train/` |
| val | 23 May 07:00 to 25 May 07:00 (2 days) | provided `train/` |
| test | 25 May 07:00 to 1 June 07:00 (7 days) | provided `validation/` |

**MIND-small** (midnight boundary):

| split | window | comes from |
|---|---|---|
| train | 9 Nov to 13 Nov (4 days) | provided `train` |
| val | 13 Nov to 15 Nov (2 days) | provided `train` |
| test | 15 Nov (1 day) | provided `dev` |

### What each split is *for*

- **train**: the past. Used for popularity statistics and slice definitions only (no learning).
- **val**: the tuning bench. Every choice you make (which encoder, what fusion weight) is
  decided by looking at val numbers.
- **test**: the final honest answer. **You look at it once, at the end, and you never make a
  decision based on it.**

That last rule is the one that sounds pedantic and isn't. If you pick your encoder because it
scored well on test, then your test score is no longer an unbiased estimate of how you'd do on
unseen data, because you *used* test to choose. You've contaminated your own answer.

**The project contains a perfect live example of this**, and it is the single best thing you
can bring up in a viva. On MIND, two encoders were compared:

| encoder | val AUC | test AUC |
|---|---|---|
| MiniLM | **0.6338** | 0.6339 |
| XLM-R | 0.6256 | **0.6364** |

MiniLM wins on val. XLM-R wins on test. The rule says choose on val, so **MiniLM ships**,
even though the test number would have been better the other way. Obeying the rule cost
0.0025 AUC. That cost is the price of the test number meaning anything at all. If you'd
switched to XLM-R after peeking at test, you couldn't honestly report either number.

---

## 6. Two different jobs, which is the thing most people confuse

The assignment asks for two things that sound similar and are not. Your code does both, and
they have separate metrics. Getting these mixed up is the easiest way to sound lost.

### Track A: re-ranking (the "leaderboard" job)

You are given the ~8 to ~24 candidates the log actually showed. Put them in order.

- Input: a small list, already filtered by whatever the real system did
- Output: that same list, reordered
- Measured by: **AUC, MRR, nDCG@5, nDCG@10**
- Files: `bm25_<split>.parquet`, `emb_<split>.parquet`, `fused_<split>.parquet`

### Track B: full-corpus retrieval (the "candidate generation" job)

Forget the pool. Search the **entire catalogue** of 20,738 (or 65,238) articles and pull out
the best 200.

- Input: nothing but the user's history
- Output: 200 article IDs out of tens of thousands
- Measured by: **recall@50, recall@100, recall@200**
- Files: `retrieval_<split>.parquet`, `retrieval_emb_<split>.parquet`

### Why both exist

The brief asks for "candidate generation to a few hundred candidates", which is Track B. But
the leaderboards score Track A. So the code does both from a single scoring pass, and reports
them separately.

**They give opposite answers, and that's a finding, not a bug.** On EB-NeRD, the semantic
scorer beats BM25 at re-ranking (+0.0198 AUC) and *loses* to it badly at retrieval
(recall@200: 0.0247 for BM25 vs 0.0150 for embeddings, about 40% worse). Ordering eight
articles somebody already decided to show you, and finding 200 needles in a 20,738-article
haystack, are genuinely different jobs. Being able to say that sentence is worth a lot.

**Track B numbers are low across the board (3 to 5% recall@200) and you should be ready to
explain why** rather than apologise for it: the EB-NeRD corpus spans articles from 2000 to
2023, while the impressions are all from May 2023. The filter only removes articles published
*after* the impression; it doesn't remove ones that are twenty years stale. Restricting the
retrievable corpus to a recency window is the obvious fix and it belongs in Component-2 with
the other behavioural signals.

---

## 7. The lexical side: BM25 and what a "query" is

### The idea

BM25 is a decades-old formula for scoring how well a piece of text matches a document. Two
sensible refinements over just counting shared words:

- **rare words count more.** Sharing "the" means nothing; sharing "Zelensky" means a lot.
- **long documents don't win just for being long.** Otherwise every long article would match
  everything.

It is the standard, boring, extremely well understood baseline in search. That's exactly why
it's here: if your fancy method can't beat BM25, your fancy method isn't working.

### What is the "query"?

This is the conceptual leap. BM25 was designed for *search*, where a human types words. There
is no typed query here. So you invent one:

> **The query is the titles of the last 30 articles this person clicked, glued together into
> one long string.**

That's `build_queries` in `retrieval/bm25.py`. If a user last read "Denmark beat Sweden 2-1",
"New striker signs for FCK" and "Coach resigns after defeat", the query becomes roughly
`"Denmark beat Sweden 2-1 New striker signs for FCK Coach resigns after defeat"`.

Then you ask BM25: of the candidate articles, which best matches that text? An article about
football will share many rare words with it. An article about tax policy won't.

This is what turns "recommendation" into ordinary text retrieval, and it's why no training
is required: **the person's history *is* the query.**

Why 30, and why titles only: news interest decays fast, and older clicks describe a person
you no longer are. A history-length sweep on EB-NeRD val showed AUC essentially flat from 1
to 100 clicks (0.4967 to 0.5059), so 30 is a reasonable default rather than a tuned magic
number, and you should say so rather than over-claim.

### Two implementation details worth knowing

**Deduplication.** A user's history is fixed within a split, so all of that user's impressions
produce the *same* query string. The code maps distinct queries to IDs and scores each once,
then fans the result out. That's why 230k MIND impressions collapse to far fewer BM25 calls.

**The Danish stopword bug, which is your best "what went wrong" story.** Stopwords are
ultra-common words ("the", "and", "is") thrown away before matching because they carry no
information. The `bm25s` library ships stopword lists for English and several other languages
but **not Danish**. So EB-NeRD was initially indexed with no stopword list at all. A query of
30 concatenated Danish titles is then dominated by Danish function words, and every article
matches every query about equally.

Supplying the standard Snowball Danish list moved val AUC from **0.5035 to 0.5232**.

The general lesson, and the reason it's worth telling: **a missing stopword list is silent.**
It doesn't crash. It doesn't warn. It just quietly makes your ranking worse, and you'd never
find it by reading the code, only by questioning a bad number.

---

## 8. The semantic side: embeddings, made and pre-made

### What an embedding is

A list of numbers standing in for a piece of text, arranged so that texts about similar
things end up with similar numbers. 300, 384 or 768 numbers per article depending on the model.

Compare two of them with **cosine similarity**, which measures whether two lists of numbers
point in the same *direction*, ignoring their length. Higher means more alike.

Why this beats BM25 in principle: BM25 needs literal shared words. "car" and "vehicle" share
no letters and score zero. Embeddings can capture that they mean nearly the same thing.

### How a user is represented

Same trick as the query, in vector form: **take the last 30 clicked articles' vectors and
average them.** That average is the "user vector", the centre of what they read. Then score
each candidate by its cosine similarity to it.

One detail worth understanding, because it's a natural viva question: the average of unit-length
vectors is *not* itself unit length, so the code re-normalises after averaging
(`retrieval/embeddings.py`). And because both sides are then unit length, FAISS's inner-product
index computes exactly cosine similarity, which is why `IndexFlatIP` is the right index.

### Pre-made vs your own

**Pre-made ("provided"):** EB-NeRD's publisher shipped ready-computed vectors for all 125,541
articles. You download and use them. Nothing to run.

**Your own:** you take a pre-trained language model off the shelf, feed it every article's
title and abstract, and it emits a vector. This is *encoding*, not training: the model's
weights are already fixed, you're just running text through it. MIND has no provided vectors,
so this was mandatory there (65,238 articles, 11m16s on CPU, cached to disk so it runs once).

### What was actually tested, and the result that matters

Four encoders were compared on EB-NeRD, semantic-only AUC on **val**, everything else held
identical:

| encoder | dim | provided or own | val AUC | beats BM25 (0.5205)? |
|---|---|---|---|---|
| **XLM-R paraphrase (own)** | 768 | own | **0.5309** | **yes** |
| word2vec | 300 | provided | 0.5098 | no |
| multilingual BERT | 768 | provided | 0.4857 | no, worse than random |

**The provided embeddings lost.** Both of them. The system ships self-encoded XLM-R vectors
(`configs/datasets.yaml:25`), and that flipped the semantic axis on Danish from losing to BM25
to beating it: `emb - bm25` went from -0.0107 to **+0.0198** on test. Best EB-NeRD test AUC
improved 0.5131 to 0.5305.

### The multilingual BERT result is your best "why" story

mBERT scored **0.4857, which is worse than ranking at random.** That is not a bug, and being
able to explain why demonstrates real understanding:

Raw, un-fine-tuned BERT vectors are famously bad at "how similar are these two texts?". Its
sentence representations all crowd into a narrow cone of the vector space where everything
looks similar to everything, and whatever variation remains tracks surface features (length,
writing register) rather than topic. Mean-pooling 30 of them compounds the problem. Scoring
*below* 0.5 means the leftover signal is mildly **anti**-correlated with clicks, plausibly
because articles that look most generic to raw BERT are exactly the filler that gets shown
often and clicked rarely.

Note the ordering defies what you'd guess from size: the 300-dimension model beats the
768-dimension one. **What matters is not how big the model is, but whether it was trained so
that cosine distance means topical similarity.** Word2Vec's objective does that, weakly. Raw
BERT's does not. XLM-R *paraphrase* does, because it was explicitly fine-tuned on paraphrase
pairs, which is precisely the "these two texts mean the same thing" objective.

That single principle predicted every encoder result in the project.

### Why different encoders per dataset

EB-NeRD uses multilingual XLM-R; MIND uses English-only MiniLM. Not inconsistency: MiniLM
spends all its capacity on English, XLM-R spreads it over 50+ languages. A specialist beats a
generalist on English, and the generalist beats a 2013 word-vector model on Danish. Each
dataset gets the best encoder available for its language, chosen the same way (on val).

---

## 9. Fusion: why and how

### Why

BM25 and embeddings are wrong about *different things*. BM25 misses synonyms; embeddings miss
rare exact terms like names and numbers. When two scorers make partly uncorrelated errors,
averaging them beats either alone, because the errors partially cancel.

### The problem you have to solve first

BM25 scores are unbounded and scale with query length (a user with a long history gets bigger
numbers on everything). Cosine similarities sit in roughly -1 to 1. You cannot just add them.

**The fix: z-score both, within each candidate pool.** For one impression's pool, subtract the
mean and divide by the standard deviation, separately for each scorer. Now both are on a
"how many standard deviations above this pool's average" scale, and comparable.

Why *within the pool* and not globally: ranking only ever happens inside one pool. That is the
only scope where the two scores need to be comparable, and normalising there automatically
cancels the query-length effect.

Then mix with one number:

```
score = alpha * emb_z + (1 - alpha) * bm25_z
```

`alpha = 0` is pure BM25, `alpha = 1` is pure embeddings.

### How alpha is chosen

Sweep 21 values (0.00, 0.05, ..., 1.00) on **val**, take the best, apply it unchanged to test.
Recorded in `fusion_alpha.json`. Grid search is fine here because it's one scalar.

The rule is the same one from §5: tuning alpha on test would mean optimising the number you
then report.

**The mixer also acts as an honest detector.** With raw mBERT vectors, alpha tuned itself to
**0.00** on demo, meaning the fusion independently decided the semantic axis was worthless and
threw it away. Nobody told it to. That's a nice thing to point at.

### Does fusion actually work? Honestly: it depends, and that's reported

| test AUC | BM25 | embeddings | fused |
|---|---|---|---|
| MIND-small | 0.5645 | 0.6339 | **0.6353** |
| EB-NeRD small | 0.5107 | **0.5397** | 0.5380 |

On MIND, fusion wins (small but statistically real). On EB-NeRD, `fused - emb` is
**significantly negative**, so fusion actively hurts: the alpha chosen on val did not
generalise to test.

**So the reported headline differs per dataset: fusion on MIND, embeddings alone on EB-NeRD.**
There is no honest reading where fused is the better EB-NeRD system, and the write-up says so
instead of quietly reporting the better number.

---

## 10. The metrics: what each one means and how they differ

All the ranking metrics are computed **per impression**, then averaged. That's what makes
slicing and bootstrapping possible. Impressions where everything or nothing was clicked are
dropped, because there's no ranking to judge.

### AUC (the headline)

*Pick one clicked article and one unclicked article at random. How often did you rank the
clicked one higher?*

- 0.5 = coin flip, no skill
- 1.0 = perfect

Computed in `eval/metrics.py` as the mean of the full clicked x unclicked comparison matrix.
It cares about the **whole ordering**, top to bottom.

### MRR (Mean Reciprocal Rank)

*Where did the first clicked article land? Score 1 / that position.*

Position 1 scores 1.0, position 2 scores 0.5, position 4 scores 0.25. Averaged over impressions.

Differs from AUC by caring **only about the top**. Whether the right answer is at rank 40 or
rank 50 barely registers; whether it's at 1 or 2 matters enormously.

### nDCG@5 and nDCG@10

*How good is my top 5 (or 10) compared to the best possible top 5 (or 10)?*

Each position gets a discount, `1 / log2(position + 1)`, so rank 1 is worth full value and
lower ranks progressively less. Sum the discounted hits, then divide by what a perfect
ordering would have scored. Dividing is the "n" (normalised) part, and it's what keeps
impressions with different numbers of clicks comparable.

Differs from MRR by handling multiple clicks properly, and by having an explicit cutoff. @5 is
stricter than @10.

### Recall@K (Track B only)

*Of the articles this person actually clicked, what share did I get into my top K, searching
the whole catalogue?*

This is the only metric for the retrieval track. It answers "is stage one even finding the
right things", which the ranking metrics can't, because they only ever see a pool that already
contains the answer.

Cold-start impressions retrieve nothing and score **0**, rather than being excluded. Excluding
them would report the recall of only the users you could already handle, which flatters you.

### Beyond-accuracy: diversity, novelty, coverage

The point of these: **a system can score well on accuracy and still be a bad product.** Showing
everyone the same five popular stories scores decently and is useless.

- **Diversity**: of the top-10 pairs, what fraction are from different categories? 1.0 means
  every slot is a different section, 0.0 means ten variations on one story.
- **Novelty**: mean `-log2(p)` where p is the article's click share in **train**. Rare articles
  carry more information, so recommending the obvious scores low.
- **Coverage**: what share of the whole catalogue ever appears in anyone's top-10. Ours is 5 to
  21%, meaning most articles are never shown to anyone by any method.

All computed from train-only statistics, so they never peek at the split being evaluated.

---

## 11. Making sure the numbers are real: bootstrap

You measured AUC 0.6353. Is that meaningfully better than 0.6339, or is it noise?

**Bootstrap**: pretend your test set is the whole world. Draw a new fake test set of the same
size by sampling impressions *with replacement* (some appear twice, some not at all). Compute
the metric. Repeat 1,000 times. The spread of those 1,000 answers tells you how much your
number would wobble with slightly different luck.

Take the middle 95%, and that's your **confidence interval**: "0.6353, somewhere between
0.6319 and 0.6360".

**Paired bootstrap** is for comparing two systems. The critical detail: both systems are
scored on the *same* resampled draw each time (`eval/bootstrap.py` reuses the same `idx`).
Two systems face identical luck, so the difference you measure isn't contaminated by which
impressions happened to be drawn.

Then the claim rule: **an improvement counts only if the 95% interval of the difference
excludes zero.** If the interval is `[-0.0003, +0.0044]`, zero is a live possibility and you
cannot claim a win.

A subtlety worth knowing: you cannot judge this by eyeballing two individual intervals. Two
overlapping CIs do *not* mean the difference is insignificant. You must build the interval on
the difference itself, which is what the code does.

**This is why scale mattered.** On `ebnerd_demo`, `fused - bm25` was +0.0020 [-0.0003, +0.0044],
which includes zero, so nothing could be claimed. At `ebnerd_small` (10x the impressions) the
same comparison became +0.0024 [+0.0017, +0.0030], which excludes zero. The effect didn't get
bigger; the interval got tighter. That's an argument about **statistical power**, not about the
method working better.

---

## 12. Leakage: the thing that's actually being graded

**Leakage** = using information you couldn't have had at the time. It's cheating, and it's
almost always accidental.

Three kinds appear here.

### 1. Future clicks in history

If a "past click" actually happened after the impression, you're predicting a click using
knowledge of that click. `pipeline/split.py` asserts every history item strictly precedes its
impression, and `tests/test_leakage.py` re-checks it from the written files.

Honest limitation, stated rather than hidden: **MIND history has no per-item timestamps, so
this check is impossible there.** The guarantee is structural (history precedes the log period)
rather than verified. The test says so instead of passing vacuously, which is much better than
a green tick that means nothing.

### 2. Post-impression columns

EB-NeRD ships `read_time`, `scroll_percentage`, `next_read_time`, `next_scroll_percentage`.
These describe what the user did *after* clicking. Using them to predict the click is circular.
They are never read by any scorer.

### 3. Serving-unavailable features (the organiser's explicit requirement)

`total_inviews` is an article's **lifetime** view count, computed across the entire collection
period. For any given impression it already knows how popular that article eventually became.
A live system serving at 8am on 24 May cannot know that.

The brief demands you report metrics **with and without** such features, so a deliberately
non-servable system `fused+popularity` exists purely to price it:

| test AUC | without | with popularity | difference |
|---|---|---|---|
| EB-NeRD demo | 0.5384 | 0.5793 | +0.0409 |
| EB-NeRD small | 0.5380 | 0.5797 | +0.0417 |

**The unservable feature is worth +0.041 AUC, which is more than the entire gain from adding
the semantic axis (+0.029).** That's the whole point of the requirement: any leaderboard
comparison that quietly includes such a feature is not measuring the same system as one that
doesn't.

`tests/test_leakage.py` enforces that no module except `eval/run.py` even mentions those
columns, so this can't leak back into a "servable" number by accident.

### 4. A retrieval-only leak that's easy to miss

`published_time` in the EB-NeRD corpus runs to 8 June, past the test window's end of 1 June.
Full-corpus retrieval must filter `published_time <= impression_time`, or the index can return
articles that didn't exist yet. This never arises on Track A, where the pool is given to you.
MIND has no dates, so the filter can't be applied there at all.

---

## 13. Offline results vs Codabench: yes, they will differ

Short answer: **yes, and substantially. Expect worse.** Four separate reasons:

**1. Different data entirely.** Your offline reports are on EB-NeRD demo/small and MIND-small.
The leaderboards score *only* the big held-out sets: EB-NeRD's `ebnerd_testset` (13,536,710
impressions) and MIND-large test (2,370,727). EB-NeRD's own guidelines say "Codabench is only
evaluating ebnerd_testset". These are far larger and drawn from different users.

**2. You cannot see the labels.** That's the point of a leaderboard. Offline you can compute
anything; there you get one number back, and EB-NeRD allows 5 submissions/day with evaluation
taking hours.

**3. The submitted system is not the reported headline system.** This is the important one and
it's documented in `pipeline/submit.py`. The MIND submission uses **embeddings alone**, not
`fused`, because BM25's scoring is dense over the whole corpus per distinct query, and at ~2M
distinct histories x 120,961 articles that's ~10^11 operations. Not practical. The cost of the
substitution is known and small (fused - emb was +0.0014 on mind_small test), and it's reported
as two different systems rather than letting the better number stand in for the uploaded one.

**4. Nothing is trained, so there's no fitting to your split.** Mild good news: a trained system
would likely degrade more when moving to different users.

Worth being able to say: the submission code is a *separate implementation* (`pipeline/submit.py`)
because the offline scorer materialises every impression at once and 13.5M impressions
(205,925,868 candidate pairs) won't fit in 15 GB. It streams instead, in 200k-impression slices
scored in 65,536-pair blocks. The **scoring semantics are identical** (mean of last 30 history
vectors, normalised, cosine), so it's the same system, executed differently. Peak memory on the
full 13.5M run was the same as on a 20,000-impression smoke test, which is the property that
matters.

---

## 14. What the results actually say

Test AUC, the headline table:

| system | EB-NeRD small | MIND-small |
|---|---|---|
| BM25 (lexical) | 0.5107 | 0.5645 |
| embeddings (semantic) | **0.5397** | 0.6339 |
| fused | 0.5380 | **0.6353** |
| fused + popularity (not servable) | 0.5797 | n/a |

Four things to be able to say about this:

1. **MIND is much easier than EB-NeRD.** 0.63 vs 0.54. Bigger, more heterogeneous candidate
   pools give a scorer more to separate. EB-NeRD's pools are small and topically tight, drawn
   from a narrow recency window, so the candidates are all plausible.

2. **Which axis wins is dataset-dependent.** Semantic wins on both, but only after switching
   EB-NeRD to a self-encoded model; with the provided encoders, lexical won on Danish.

3. **Fusion helps on MIND and hurts on EB-NeRD**, and both are reported rather than
   cherry-picked.

4. **MIND's 0.635 from an entirely unsupervised, content-only system is respectable**: the
   published neural baselines for MIND-small (NAML, NRMS, LSTUR) sit around 0.65 to 0.67, and
   those are trained models.

---

## 15. Questions you should rehearse

- *What did you train?* Nothing. It's a similarity-based retrieval system; the only tuned
  parameter is one fusion weight, chosen on val.
- *What's the query?* The titles of the user's last 30 clicked articles, concatenated.
- *Why not a random split?* It would let the system use the future to predict the past.
- *Why is your test set only looked at once?* Because using it to choose anything makes it stop
  being an honest estimate. Point at the MiniLM/XLM-R reversal on MIND.
- *Why did multilingual BERT score below 0.5?* Raw BERT vectors aren't trained so that cosine
  distance means topical similarity; everything crowds into a narrow cone.
- *Why is recall so low?* The corpus spans 2000 to 2023, impressions are from May 2023, and the
  filter only removes future articles, not stale ones.
- *Is your improvement real?* Only where the paired bootstrap CI excludes zero, and there are
  places (demo-scale fusion) where it doesn't and nothing is claimed.
- *What can't you check?* Per-click leakage on MIND, because its history has no timestamps.
- *What's the biggest single lever?* The serving-unavailable popularity feature, +0.041 AUC,
  which is why the brief makes you report without it.

---

## 16. Where to read next

- `GLOSSARY.md` (same folder) defines every term on its own, if a word here was unfamiliar.
- `NOTES.md` (same folder) is the evidence trail: measured schemas, every decision, every
  ablation with its confidence intervals. Longer and denser than this, and the place to go when
  you want the numbers behind a claim rather than the explanation of it.
- `../deliverable/DESIGN_NOTE.md` is the 4-page write-up that gets graded.
- `../results/` holds the generated reports, one per dataset and split.

If you find a disagreement between this file and `NOTES.md`, trust `NOTES.md`: it is written as
the work happens, and this is a summary of it.
