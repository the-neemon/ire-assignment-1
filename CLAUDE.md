# CLAUDE.md

## Project

IRE Assignment-1 — news recommendation on EB-NeRD and MIND. `brief/Assignment1_v1.pdf` is the
authoritative assignment text; `brief/SPEC.md` is the original build plan, kept for history.
Component-1 (lexical + semantic retrieval, data pipeline, eval harness) is solo and due 27 Aug;
Component-2 (behavioural signals, re-ranker, serving analysis) is a pair project due 10 Sep and
builds directly on the Component-1 repo.

Documentation lives in `docs/`: `WALKTHROUGH.md` (how the system works, plain English),
`NOTES.md` (measured data facts and every decision's justification), `GLOSSARY.md` (terms).
Graded output lives in `deliverable/`.

Project-specific hard rules:

- **Splits are temporal, never random.** Interaction data must be split by time; train strictly
  precedes val strictly precedes test.
- **No future-click leakage.** Every feature value used for an impression must be computable strictly
  before that impression's timestamp. This is enforced in code, not by discipline.
- **Report metrics with and without serving-unavailable features.** Organizer requirement.
- **Grading includes a live viva** ("explain-and-modify" on the repo). Prefer code the author can
  explain and change on the spot over code that merely runs. This makes the global simplicity rules
  load-bearing here, not stylistic.
