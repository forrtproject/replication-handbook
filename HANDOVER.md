# Handover: open MetaROR revision issues

Written 2026-08-16 after a batch of ten small PRs (#67–#76). This file tells the next agent how work in this repo is done and what remains, issue by issue. Delete it once the listed issues are closed.

## How work is done here

- **Repo**: Quarto book (`_quarto.yml`), chapters are the top-level `*.qmd`, bibliography `references.bib` (keys `AuthorEtAlYYYY`, sorted alphabetically). Rendered site lives in `docs/` and is rebuilt by CI on push to `main`; never commit `docs/`.
- **Main is admin-only.** Any content change (prose, bib, figures, tables) goes through a PR. `metaror_todo.md`, `_quarto.yml` build settings and this file are the only things committed to `main` directly.
- **Branch and PR conventions**: branch `content/issue-NN-<slug>` off `origin/main` after `git fetch`; one issue per PR; commit messages imperative, ending `(#NN)`, no `Co-Authored-By` line; PR title ends `(#NN)`, body is a self-contained statement of the change for co-authors (no process narration), ending `Closes #NN`.
- **House style**: commas rather than dashes for asides; plain academic prose; text has no memory of its drafts (never "no longer", "rather than the previous"); citations in pandoc form. Never invent DOIs: verify via `https://api.crossref.org/works/<DOI>`.
- **Verify before pushing**: `quarto render <chapter>.qmd --to html` and check for `Citeproc` warnings or `?@`. Single-chapter renders always warn `Unable to resolve crossref @sec-differences-and-interpretation` / `@sec-appendix-templates`; that is benign (targets live in other chapters). Then `git checkout -- docs; git clean -fdq docs`.
- **PR review site**: every PR is rendered as tracked changes at <https://forrt.org/replication-handbook/pr-review/> (`tools/pr-review/`), so co-authors review book text, not diffs.
- **External reviews**: for non-trivial prose, run codex (statistics/method accuracy, `codex-delegate` skill, read-only) or agy (style/flow, `agy-delegate` skill) on the diff before opening the PR. Run them in the foreground with a long timeout; a subagent that backgrounds the review tends to stop before reading the answer.
- **Parallel subagents**: one worktree per issue works well. Give each a full brief (file, line anchors, what to write, which review). Assign distinct sections when two PRs touch the same file. Read every diff yourself before reporting.

## Open PRs (as of writing)

| PR | Issue | Note |
|---|---|---|
| #67 | #45 | How to Cite shown only in PDF |
| #68 | #49 | FReD → FLoRA; touches `publishing.qmd` table row, may need a trivial merge with #36 |
| #69 | #54 | Table 2.1 removed |
| #70 | #63 | one-clause change in `planning.qmd` |
| #71 | #53 | `lightbox: true` |
| #72 | #55 | adversarial collaborations merged into original-authors section |
| #73 | #61 | FAIR callout in Feasibility |
| #74 | #56 | multiverse row removed, paragraph added to Ch5 Analysis; touches `execution_reproductions.qmd` + `references.bib` like #76 |
| #75 | #64 | mini meta-analysis paragraph in Ch3 Uncertainty |
| #76 | #57 | forensic metascience paragraph in Ch4, data-inspection paragraph in Ch5, Figure 4.1 PNG re-lettered |
| #43, #38, #36 | #23, #2, #21 | older PRs from June, still open |

Merge #74 and #76 one after the other and re-render; both touch `execution_reproductions.qmd` (different sections) and `references.bib` (different entries).

## Remaining specific issues, with pointers

Ordered roughly by effort. All are content, so PR each.

### Small
- **#3 Broken citations** – collector issue; the three listed are fixed. Grep rendered HTML for `(20\d\d)` preceded by nothing, or `?@`, after the batch above merges; close if clean.
- **#48 Contacting Authors / Identification of Claims are relevant to replication too** – `execution_reproductions.qmd` `## Contacting Authors` (~l. 66) and `## Identification of Claims` (~l. 83); `execution_replications.qmd`; `discussion.qmd` `## Comments from the Original Study's Authors` (~l. 224). Minimum: add cross-references from the replication chapter to those two sections and from the reproduction chapter to the Comments section. Moving them to Ch3/4 is a bigger call; the issue accepts cross-references.
- **#50 Move Chapter 8 into the process part** – `_quarto.yml` `book: chapters:` (~l. 248): move `publishing.qmd` from "Advanced Topics and Applications" to the end of "The Reproduction and Replication Process". Check chapter-number references in prose (`grep -n "Chapter 8\|Section 8" *.qmd`). Coordinate with #36 (open PR on publishing.qmd).
- **#12 New findings on replication success** – belongs in `discussion.qmd` `## Defining and Determining Replication Success`; check the issue body for the papers to add.

### Medium
- **#58 Move Figure 4.2 to 7.2** – Figure 4.2 is `@fig-replication-sequence` (`images/6sH_Image_4.png`, `planning.qmd` ~l. 113–140, section "Close replication before conceptual replication"). Target: `discussion.qmd` `## Interpreting Divergent Results` (~l. 110); use the figure to say that how a failure is read depends on the replication type. Also rename `## The Role of Differences for the Interpretation of Findings` (~l. 196, `{#sec-differences-and-interpretation}`) to "Inductive vs deductive perspectives on replication failure" and reduce overlap with `### Hidden Moderator Account`. Keep the anchor id, it is cross-referenced from `planning.qmd` and `understanding.qmd`. The figure is a PNG with no vector source.
- **#52 Researcher Bias → personal motivation** – `choosing_study.qmd` `## (Potential) Researcher Bias` (~l. 277). Reshape into a section on the researcher's own motivation for choosing a target: beyond feasibility, legitimate motivations, problematic ones worth avoiding, and confirmation bias when setting out to challenge a claim. Source to draw on: <https://doi.org/10.5281/zenodo.18808378> (read it first; verify metadata before citing).
- **#60 "Doing the same" is hard + Altmetric donuts** – two parts. (a) Somewhere in `execution_replications.qmd` (Analysis or the sample/procedure sections): replicating "the same" analysis is ambiguous (same covariates vs same covariate-selection rule); justify the choice and add robustness checks for the sensible alternative. (b) `choosing_study.qmd` `## Value` (~l. 110) mentions Altmetric; add a short explanation with two example donuts (needs images; Altmetric badges can be embedded from `https://badges.altmetric.com/`, or screenshot two donuts into `images/` with attribution). Ask Lukas which two papers.
- **#47 Rework Chapter 1** – `background.qmd`; add a "why should I care" section (career incentives: not yet highly rewarded, but a way to learn, build skills and connections, signal commitment to robustness and open science) and a "how to use this handbook" section. Overlaps with the R3 suggestion to merge Ch1 into Ch2 (#27), which the authors have not adopted; do not merge.
- **#51 Split Table 7.1** – `discussion.qmd` `## Defining and Determining Replication Success` (table built in R code). Split into reproduction criteria (move to Ch5) and replication criteria; decide with Lukas whether all rows are needed.
- **#59 Balance reproduction coverage in Ch2** – `understanding.qmd` `## Reproduction and Replication` (~l. 51) and `planning.qmd` Table 4.1 (`@tbl-rep-types`, ~l. 46). Move the classification into Ch2 and create two subsections: reproductions (numerical vs robustness, their value) and replications (existing material). Note the merged restructure PR #33 already synthesised Ch2 "types" with the Ch4 typology; read `understanding.qmd` `## Closeness and Similarity` before changing anything.

### Larger / need Lukas
- **#8 Authorship statement** – narrative CRediT-style statement; needs input from Lukas on who did what. `contributions.qmd` exists.
- **#44 Example boxes** – collect candidate example studies per chapter; ask Lukas before drafting.
- **#1 Ideas for v0.2** – parking lot, do not act.
- Umbrella issues #14–#29 track the reviewer todo list (`metaror_todo.md`); tick items there on `main` when a PR merges. Do not open PRs against umbrella issues; open them against the specific sub-issue or name the umbrella in the PR body.

## Judgment calls already made (do not reopen)
- FLoRA expansion is "FORRT Library of Replication Attempts" (matches the OSF citation and `background.qmd`), even though the FORRT page header says "Reproduction and Replication Attempts".
- OSF and Harvard Dataverse are general repositories, not curated archives; the FAIR box (#73) says so.
- Figure 4.1 was patched as a raster; if the figure is redrawn for #17, do it in a reproducible format (mermaid or R) and drop the PNG.
- Red teams are out of scope for the handbook (#55).
- `LakensEtAl2018` is the equivalence-testing tutorial; only cite it for that.
