# Glossary — every term in this assignment, in plain English

Written for someone new to the subject. Terms are grouped by what they're for, not alphabetically,
because that's the order they make sense in.

Tags: **[used]** we built it · **[named]** the brief mentions it, we didn't use it ·
**[tooling]** not from the course at all

---

## 1. Words for the data itself

**Impression** **[used]**
One moment when a list of articles was shown to one person. Your data is millions of these.
Each one records: who, when, what was shown, what was clicked.

**Candidates** **[used]**
The articles in that shown list. These are what you have to put in order.

**Click history** **[used]**
The articles that person read *before* this moment. Your main clue about what they like.

**Session context** **[named]**
Extra details of the moment — time of day, device used. We didn't use these.

**Corpus** **[used]**
All the articles you have. The whole collection.

**Catalogue** **[used]**
Same thing as corpus. Used interchangeably.

---

## 2. The three kinds of clue (the "three axes")

The brief keeps saying "all three modelling axes". It just means these three kinds of clue:

**Lexical** **[used]**
To do with the actual *words*. Matching because two texts share the word "football".

**Semantic** **[used]**
To do with *meaning*. Matching "car" with "vehicle" even though they share no letters.

**Behavioural** **[named]**
To do with what people *do* — what's popular, what's recent, what they clicked lately.
This is the follow-up assignment, not this one.

---

## 3. Matching on words

**BM25** **[used]**
A recipe for scoring word overlap between what you're searching with and each document.
Two sensible adjustments over naive counting:
- rare words count for more than common ones
- long documents don't win just for containing more words

It's the standard baseline in search — decades old, very well understood.

**TF-IDF** **[named]**
An older, simpler version of the same idea. TF = how often a word appears here.
IDF = how rare that word is overall. Multiply them. BM25 is the refined descendant.

**Inverted index** **[used]**
A lookup table from *word* → *which documents contain it*. Exactly like the index at the back of
a textbook. It's what makes word search fast — you never scan every document.

**Stopwords** **[used]**
Extremely common words — "the", "and", "is" — that carry almost no meaning, so they get thrown
away before matching. **This caused the biggest bug in the project:** no Danish stopword list
existed, so the Danish results were almost random until I supplied one.

**Stemming** **[used]**
Chopping words back to a root so "running", "runs" and "ran" all match each other.
Has to be done per-language.

---

## 4. Matching on meaning

**Embedding** (also called a **vector**) **[used]**
A long list of numbers standing in for a piece of text, arranged so that texts about similar
things get similar numbers. Ours are 768 numbers per article (Danish) or 384 (English).

**Encoding vs training** **[used]**
Worth separating, because they sound alike. *Training* changes a model's internal weights.
*Encoding* runs text through a model whose weights are already fixed and keeps the numbers that
come out. We only ever encode. Nothing in this component is trained.

**XLM-RoBERTa** **[used]** — *what ships for Danish*
Like BERT, but trained on many languages at once. The assignment allows either the provided
embeddings **or** computing your own with BERT/XLM-RoBERTa, and we do the latter:
`paraphrase-multilingual-mpnet-base-v2`, an XLM-RoBERTa fine-tuned on paraphrase pairs, 768
numbers per article. It beat both provided encoders on validation (0.5309 vs 0.5098 and 0.4857)
and is the only one that beats BM25 on Danish.

**MiniLM** **[used]** — *what ships for English*
The small, fast embedding model used for MIND, 384 numbers per article. English-only, and it
beats the multilingual XLM-R on English validation data (0.6338 vs 0.6256). A specialist beats
a generalist on its own language; the reverse holds on Danish, which is why the two datasets
use different encoders.

**Word2Vec** **[tested — not used]**
An older way to make embeddings — one fixed vector per word. The newspaper published ready-made
Word2Vec vectors for every article, and they are one of the two options the brief offers. Kept
as an ablation comparison, but it lost to our own XLM-R vectors (0.5098 vs 0.5309 on validation)
and loses to BM25, so it does not ship.

**BERT** **[tested — and rejected]**
A neural network that reads a whole sentence and produces embeddings that depend on context,
so "bank" in "river bank" and "bank account" come out different. We tested the multilingual
version on Danish and it scored **worse than random** (0.4857). Why: BERT's raw vectors are
famously bad at "how similar are these two texts?" unless someone fine-tunes them for exactly
that job. Straight out of the box, everything looks similar to everything else.

The general rule this taught us, which predicted every later encoder result: what matters is not
how big a model is, but **whether it was trained so that cosine distance means topical
similarity**. Word2Vec's objective does that weakly, raw BERT's not at all, and XLM-R
*paraphrase* does it directly — which is why the 300-number model beat the 768-number one, and
the fine-tuned 768 beat both.

**Cosine similarity** **[used]**
How we compare two embeddings. Gives a number where higher = more alike. It compares *direction*
only, ignoring size — so a long article and a short one about the same topic still match.

---

## 5. Finding the good ones quickly

**Top-K** **[used]**
The K best results. "Top-200" = the 200 highest-scoring articles.

**Nearest neighbour** **[used]**
The most similar item to the thing you're holding.

**ANN — Approximate Nearest Neighbour** **[used]**
Finding the most similar items *quickly*, by accepting "very close" instead of insisting on
"provably the closest". You need this when there are millions of items, because checking every
one is too slow.

**FAISS** **[used]** / **ScaNN** **[named]**
Software libraries that do that search. FAISS is Meta's, ScaNN is Google's. We used FAISS.

**Flat index / brute force** **[used]**
Checking every single item, no shortcuts. Exact, but slow at large sizes.
At our size it was fast enough, so that's what we used.

**IVF / PQ / quantisation** **[named]**
Tricks to make the search faster by being slightly less exact. We didn't need them, but the
report explains when you would.

**Candidate generation** **[used]**
Stage one: narrowing the whole collection down to a few hundred worth a closer look.

**Re-ranker** **[named]**
Stage two: carefully ordering those few hundred with a trained model. **Not this assignment.**

**Two-stage retrieve-then-rank** **[used]**
The overall pattern: cheap narrowing first, expensive careful ordering second.

**GBDT — Gradient Boosted Decision Trees** **[named]**
A kind of machine-learning model that works well on table-shaped data. Suggested for the
re-ranker in the follow-up.

---

## 6. Scoring how good you are

**AUC** **[used]** — *the headline number*
Pick one article they clicked and one they didn't. How often do you rank the clicked one higher?
- 0.5 = coin flip
- 1.0 = perfect

**MRR — Mean Reciprocal Rank** **[used]**
If the clicked article lands at position 1 you score 1; position 2 scores ½; position 3 scores ⅓.
Averaged over everything. Rewards getting the right answer *very* near the top.

**nDCG@5 / nDCG@10** **[used]**
"How good is my ordering in the top 5 (or 10), compared with the best possible ordering?"
1.0 = perfect. The @5 / @10 is just how far down the list you look.

**Recall@K** **[used]**
Of the articles the person actually clicked, what fraction did you manage to get into your top K?
This measures whether stage one is even finding the right things.

---

## 7. Measures that aren't accuracy

The brief calls these **beyond-accuracy**. The point: a system can score well and still be bad.

**Diversity** **[used]**
Are your ten recommendations all about the same thing, or a mix? Ten football stories = not diverse.

**Novelty** **[used]**
Are you showing obscure things, or only what everybody already reads?

**Coverage** **[used]**
Across everything you recommend to everyone, what share of the whole collection did you ever show?
Ours was 5–21% — meaning most articles never get shown to anyone, by any method.

---

## 8. Looking at subgroups

**Slice / slicing** **[used]**
Checking your score for one subgroup instead of everybody, because an average can hide that
you're terrible for some people.

**Cold-start** **[used]**
Someone you know almost nothing about — a brand-new user with no reading history.
There's nothing to match against, so it's the hardest case.

**Warm** **[used]**
The opposite: plenty of history to work with.

**Head vs tail** **[used]**
Head = popular items. Tail = rarely-touched items. Most items are tail.
Systems usually look good on head and bad on tail.

---

## 9. Splitting the data, and cheating

**Temporal split** **[used]**
Dividing your data by *time*: earliest chunk to build on, middle to tune with, latest to test on.

**Random split** **[forbidden]**
Dividing rows randomly. **Banned in this assignment**, because it lets you learn from the future
to predict the past. That inflates your score and means nothing.

**Train / validation / test** **[used]**
Three chunks. *Train* = build on it. *Validation* = tune your choices on it.
*Test* = your final honest score — you look at it once, at the end.

**Leakage** **[used]**
Using information you couldn't possibly have had at the time. Cheating, usually by accident.

**Future-click leakage** **[used]**
The specific version here: using a click that happened *after* the moment you're predicting.

**Behaviour-window boundary** **[used]**
The cut-off line. History must come from before it, predictions from after it.

**Serving time** **[used]**
The moment a real system would have to make this recommendation, live.
If a piece of information doesn't exist yet at that moment, you're not allowed to use it.

**Serving-unavailable feature** **[used]**
Data that only exists later. Example: an article's total lifetime view count — that's only known
after the fact. Using it inflates your score dishonestly. The brief demands you report your
numbers both with and without such features. Ours: it was worth +0.041 AUC, more than our entire
meaning-matching method gained.

**Anti-gaming** **[used]**
The brief's rules to stop you inflating your numbers, accidentally or otherwise.

**Ablation** **[used]**
Changing exactly one piece and re-measuring, to prove that piece actually mattered. We ran four:
the embedding encoder (`make encoder-ablation`, same data and code, only the vectors swapped),
stemming, compound-splitting, and which article fields to index. Two of the four rejected the
idea being tested, which is the point of running them.

The rule that makes an ablation honest: **choose the winner using the validation set, never the
test set.** If you pick using test, the test score stops being an honest final answer, because
you used it to make a decision. Same idea as [[temporal split]] — don't peek at the answer.

The sharpest example here: on MIND, MiniLM wins on validation and XLM-R wins on test. The rule
says choose on validation, so MiniLM ships even though the other test number looks better.
Obeying the rule cost 0.0025 AUC, and that cost is what makes the test number mean anything.

---

## 10. Being sure your numbers are real

**Bootstrap** **[used]**
A way to find out how much your score would wobble if you'd happened to collect slightly
different data. You re-draw your data at random (with repeats allowed) many times — we did 1,000 —
and watch how much the answer moves.

**Confidence interval (CI)** **[used]**
The resulting range. "0.64, somewhere between 0.63 and 0.65."

**Paired bootstrap** **[used]**
Comparing two methods on the *same* re-drawn data each time. Fairer, because both methods face
identical luck.

**"the CI excludes zero"** **[used]**
Means an improvement is real rather than noise. If the range of the *difference* between two
methods includes zero, they might genuinely be equally good and you can't claim a win.

---

## 11. Admin words

**Leaderboard** **[used]** — a public ranking of everyone's submissions.
**Codabench** **[used]** — the website hosting the two leaderboards you must submit to.
**Design note** **[used]** — the report you hand in, 4 pages maximum.
**10× scale** **[used]** — "what would break if this got ten times bigger?"
**Viva** — the live conversation where you explain and modify your own code.

---

## 12. Tooling words — NOT from your course

You don't need these for the assignment. Listed only because they've come up.

**ADR — Architecture Decision Record** **[tooling]**
A short note recording why a technical choice was made. It came from a plugin, not your course.

**Parquet** **[tooling]** — a file format for tables. Smaller and much faster than CSV.
**Polars** **[tooling]** — the library we use to handle tables. Like pandas, but faster and lighter.
**Streaming** **[tooling]** — processing data in chunks rather than loading it all at once.
**OOM (Out Of Memory)** **[tooling]** — the program asked for more memory than existed and was killed.
**RSS** **[tooling]** — how much memory a program is actually using right now.
**SLURM** **[tooling]** — the job scheduler on your university GPU cluster.
