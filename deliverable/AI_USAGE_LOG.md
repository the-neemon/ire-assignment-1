# AI usage log

## 1. Tools used

| tool | used for |
|---|---|
| Claude Code (CLI, VSCode extension) | all implementation, refactoring, documentation, and analysis in this repo |
| Kaggle notebook (T4 GPU) | `sentence-transformers` inference for the self-encoded embedding arm |

I didn't use any other assistant. Every line of code here passed through Claude Code.

I switched models during the project, and the transcript records which one answered each turn,
so these are measured rather than asserted:

| model | turns | what for |
|---|---|---|
| Claude Opus 5 | ~2,470 (80%) | my default: planning, the pipeline, the eval harness, the encoder switch, the design note, the final audit |
| Claude Sonnet 5 | ~530 (17%) | the encoder ablation and the MIND ablation batch, 20-23 Aug: scripted work against a plan that already existed |
| Claude Haiku 4.5 | 76 (2%) | the harness's own background model, not a choice I made |

The Sonnet window is three days, not a standing policy, and Opus handled plenty of small tasks
too. The first two counts are approximate because the session was still running as I wrote this.

## 2. Chat transcript

The complete session history is `deliverable/transcripts/transcript.json`: 6,338 records
covering 1 to 24 Aug, every day I worked. It's JSON Lines, one record per line, so read it line
by line rather than parsing the file as a single JSON document.

**It's merged from two exports, so here is exactly what I did to them.** The harness forked the
session on 1 Aug at 16:42, leaving two files that shared a 250-record header and were otherwise
almost disjoint: 2 to 15 Aug existed only in the first, 19 to 24 Aug only in the second. Shipping
either alone would have hidden half the project. Merging them:

- **deduplicated** the 250 shared header records;
- **sorted** the rest by timestamp, ties broken by original position;
- **dropped 3,135 harness bookkeeping records** (`mode`, `permission-mode`, `ai-title`,
  `file-history-*` and similar), which carry no timestamp and no conversation content;
- **changed no record content.** I verified this: all 6,338 lines are byte-identical to their
  source lines, and no conversation record from either export is missing.

What remains is 1,745 user records, 3,104 assistant, 1,318 attachments and 212 system records, in
the order they happened, unedited. It's a snapshot taken on 24 Aug while I was still finishing
the submission, so the last few minutes of the session fall outside it. Record numbers in §3 are
indices into this file.

I re-checked the logs at export: no credentials or API tokens, and the only personal identifier
is my own email, from the git commit author field.

## 3. Key prompts

Seven prompts that changed the direction of the build, quoted verbatim with record numbers so
they can be found without reading all 6,338.

**Scoping, before any code existed** (record #69, 2026-08-01T15:17):
> "ok, now let's start with with assignment, read the md files and tell me where and how we
> should start"

This put the session into plan mode before implementation.

**The question that triggered the field ablation** (record #3714, 2026-08-17T11:15):
> "if eb-nerd dataset contains the article bodies are we using them?"

I didn't know the answer, and neither did the agent from measurement: the field choice had never
been tested. This turned an unexamined default into a run ablation.

**The directory restructure** (record #3764, 2026-08-17T16:55):
> "fix the directory structure, right now everything is scattered and anything is hard to find,
> give me options how you'll structure it"

I picked from the options I was given, which produced the current layout.

It could be reproduced, so I had the file renamed rather than overwritten.

**Ruling out the fused system** (record #5118, 2026-08-23T05:59):
> "fix the scaling claims but know that I dont want a fused submisison, also can ablations 2 and
> 3 be combined? is 3 on a fused system?"

Two decisions. Pushing on the scaling claim got it measured instead of estimated (§7). Ruling out
fusion changed what the remaining ablations were measured against: the MIND entity signal had to
be evaluated on embeddings alone, or the reported gain wouldn't describe the shipped system.

**Re-verifying every claim before submitting** (record #5822, 2026-08-24T13:24):
> "verify all of the claims and double chekc any information in the design note or any other
> place, find anything wrong or contradicting and fix them"

This sweep found five factual errors in prose I had already read once (§7). What prompted it was
catching one myself at record #5790: the design note still said both datasets used the last 30
clicks after I'd changed MIND to 100. One accidental find made me stop trusting the rest.

## 4. What I delegated, phase by phase

Dates are from artifact mtimes and git history, not memory.

| date | phase | what I had the agent do |
|---|---|---|
| 1 Aug | scoping | Read the assignment, write `SPEC.md`, explain Component-1. Plan mode before any code. |
| 1-2 Aug | pipeline | Environment and dependencies; `pipeline/download.py`; temporal split with integrity assertions; BM25. |
| 4-5 Aug | scale + submission | EB-NeRD test set; streaming Codabench submitter; MIND-large submission. |
| 10-11 Aug | semantic axis + eval | Embeddings and FAISS retrieval; fusion; the eval harness; the encoder ablation; first design note. |
| 17 Aug | comprehension + hygiene | The field ablation; directory restructure; my first git commit. |
| 19-20 Aug | final encoder | Switch to `Ekstra_Bladet_contrastive_vector`; full EB-NeRD re-run; Codabench submissions and scores. |
| 20-21 Aug | encoder ablation | Four sentence-transformer encoders on MIND val, picked on measured AUC against resource cost. |
| 23 Aug | MIND ablations + fix | Per-dataset `history_len`; the entity-overlap signal; six ablations; the smoke-test overwrite fix (§7). |
| 24 Aug | design note + audit | Rebuilt the design note in LaTeX; ran the claim-verification sweep; repo hygiene; final commits. |

I didn't delegate this as one instruction. I scoped it in plan mode, approved the plan, then had
the build proceed in stages, answering design questions before it wrote code. The open decisions
it surfaced (which retrieval framing, which dataset scale, which encoder) were mine. That said, I
gave it several individual tasks larger than the lecture recommends, and the partial-run
incidents in §7 are the direct consequence.

**The commit gap.** File history runs from 1 Aug; my first commit is 19 Aug. Two separate things
sit in that gap.

I hadn't pushed a repo before 19 Aug because the course used GitHub Classroom, which was
discontinued, and the TA only told us on 18 Aug to push to our own repos meanwhile. I committed
the day after that announcement. Until then there was no course-specified place to push to.

Only making one commit once a repo existed is a genuine gap, and I'm recording it as one. I could
have kept local git history from day one and didn't; that single commit covers all 87 files and
16,424 lines in one shot. I never reviewed changes via `git diff` during the build, because there
was no history to diff against. What stood in for it, imperfectly, was the harness's diff view on
each edit plus the practices in §8. Those catch behavioural bugs; they don't substitute for
reading every line as it lands. After 19 Aug there are seven further commits through 24 Aug, each
scoped to one change, so the gap is confined to the first eighteen days.

## 5. Context management

- **I compacted manually.** This was one long context resumed across
  the whole project cmpacted regularly. The export confirms
  two manual compactions:

  | when | tokens before -> after |
  |---|---|
  | 2 Aug, 03:53 | 287,337 -> 12,736 |
  | 10 Aug, 06:28 | 386,823 -> 12,746 |

  Both sit near
  290-390k tokens, which makes them reactive rather than triggered on contradiction or confusion.

## 6. AI-generated vs. human-written code

- **Claude Code wrote every source file** in `pipeline/`, `retrieval/`, `eval/`, `tests/`,
  `scratchpad/`. I didn't hand-type any of them.
- **Claude Code drafted every piece of prose** in `docs/` and `deliverable/`. I checked each
  against the underlying artifacts rather than the agent's say-so; §7 lists where that found the
  prose wrong.
- **The decisions were mine:**
  - to build both the re-rank and full-corpus retrieval tracks, not just one
  - to target `ebnerd_demo` + `mind_small`, scaling to `ebnerd_small`
  - to adopt `Ekstra_Bladet_contrastive_vector` as the shipped EB-NeRD encoder
  - to leave the serving-unavailable popularity feature out of the leaderboard entry
  - to use per-dataset history lengths once the sweep showed the datasets disagreed
  - not to ship a fused submission, which changed what the later ablations measured against
  - to use the two-column design note, because one column in four pages meant unreadable type

`docs/NOTES.md` ships, as the evidence trail behind every number in the design note.

## 7. What worked, and what failed

**The one that got past every check and reached the leaderboard**, which is the worst thing that
happened in the project:

| what | how it surfaced | outcome |
|---|---|---|
| A smoke test silently overwrote a real submission | I uploaded it and Codabench scored 0.5012, which is random | `--limit N` wrote to the same path as a full run, so a 20,000-line smoke test replaced a complete 2,370,727-line submission. Nothing errored, no test failed, the file looked normal. I fixed it structurally rather than by resolving to be careful: `--limit` now writes to a `SMOKE-` prefixed path and says it isn't submittable. Verified by checksumming the real submission across a `--limit 5000` run. |

**Caught by measurement:**

| what | how it surfaced | outcome |
|---|---|---|
| No Danish stopword list (`bm25s` ships none) | EB-NeRD AUC near random, unresponsive to history length | Supplied the Snowball Danish list: val AUC 0.5035 -> 0.5232. A missing stopword list degrades ranking without erroring. |
| Raw multilingual BERT scored below random (0.4857) | Encoder ablation on val | Not a bug: un-fine-tuned BERT vectors mean topical similarity, not relevance. Fusion drove its alpha to 0.00 independently. |
| `.to_list()` memory blow-up, three separate times | OOM kill at 10 GB RSS (confirmed in `dmesg`), then twice more in other files | Replaced with `explode().to_numpy()`. Peak 5.8 GB down sharply, byte-identical output. See §5. |
| MIND submission was never actually streaming | OOM-killed after 200k of 2.37M impressions | CSV has no slice pushdown; added a one-off parquet conversion. Peak 4.2 GB -> 2.86 GB, first 20,000 lines byte-identical. |
| recall@K missing from every report | I re-read the brief against the harness | `eval/run.py` never opened the retrieval files. Added with CIs and slices. |
| Entities parsed then silently dropped | I re-read Q1.4 against `_mind_news` | Present in the `.select()` upstream, absent downstream. |
| BM25 document fields were an untested assumption | I asked directly (§3, record #3714) | Ablation: body costs -0.0166 AUC. The shipped choice was right, but had never been measured. |
| Design note carried numbers a rebuild had superseded | Cross-checked the note against `results/` | Tables had drifted from the artifacts they described. |
| A scaling claim was asserted, never timed | I pushed back directly (§3, record #5118) | "Not practical" rested on an untimed operation count. Measured: 1.6 ms/query, about 1.6 hours. The original is marked superseded in `NOTES.md` rather than edited away. |

**Caught by verification:**

| what | how |
|---|---|
| Two partial runs left mixed-encoder artifacts | A crash killed the run mid-way, so embeddings used the new encoder while fusion and reports were still from the old one. Caught by comparing artifact mtimes against the config mtime, not from any error. Fixed both times with a clean re-run. |
| A diff that looked like a regression wasn't | I was comparing against the partial output of an OOM-killed run, not the smoke test. |
| Five design-note claims wrong or self-contradictory | The sweep at §3, record #5822, after I found the first by accident. Reading prose and checking it against artifacts are different activities. |
| A submission was attributed to the wrong encoder | The agent mapped `893893` to `contrastive_vector`. My screenshots show `895220` is contrastive (0.5381) and `893893` is XLM-R (0.5336). The comparison built on the wrong mapping was dropped, not rewritten. |
| Two screenshots had swapped filenames | `ebnerd.png` held the MIND row and vice versa. Caught by opening the images. |
| A LaTeX macro failed silently | `\text{}` without `amsmath` mangled both fusion formulas while still producing a clean-looking PDF. Caught by reading the build log. |

**Where I overrode the agent, or it overrode me:**

| what | outcome |
|---|---|
| I asked whether to add lifetime popularity to the leaderboard entry | It advised against: the feature is 85% null, so the offline gain wouldn't transfer. Left out. |
| It told me which submission used which encoder, and was wrong | Corrected from my own screenshots. The one case where it stated something confidently, no test would catch it, and only my record of what I'd uploaded settled it. |
| I had a second AI review this log against the lecture slides | Adopted two findings as diagnosed; adopted the third (context management) in substance but rewrote it, because the causal claim wasn't supported by the transcript. |

## 8. Verification practices I used

- **Assertions in the build, tests outside it.** `pipeline/split.py` asserts while building;
  `tests/test_leakage.py` (19 tests) re-checks the same properties from the written artifacts.
- **I verified the leakage suite wasn't vacuous** by injecting a future click into one history
  and confirming the assertion fired. A suite that has never failed proves nothing.
- **Byte-identical rebuilds.** Outputs are sorted on a unique key before writing, because
  `polars.unique()` is hash-ordered; verified identical across three consecutive runs.
- **Independent recomputation.** Validated submissions on all 13,536,710 lines, plus 40 random
  impressions per dataset re-ranked in float64 through a separate code path.
- **I selected on val, never test.** On MIND, MiniLM wins on val and XLM-R on test. I shipped the
  val-chosen model anyway, costing 0.0025 test AUC.
- **When a check didn't exist, I built one.** The smoke-test overwrite couldn't be caught by any
  test I had, so I changed the tool instead. The practice I'd most want to carry into Component-2.
