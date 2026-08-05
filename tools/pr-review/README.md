# PR review site (tracked changes)

Renders the chapters touched by each open pull request as HTML with the changes
marked up like tracked changes in a word processor, so PRs can be reviewed as
book text rather than as a source diff.

```bash
python3 tools/pr-review/build_review.py --serve     # all open PRs, then open in a browser
python3 tools/pr-review/build_review.py 42 35       # only these PRs
python3 tools/pr-review/build_review.py --clean     # discard the cache and rebuild
```

Needs `gh` (authenticated), `git` and `quarto`. Output goes to `pr-review/`
(git-ignored); rebuilds skip PRs whose head commit has not moved.

## Published version

`.github/workflows/pr-review.yml` rebuilds the site on every PR opened, updated,
reopened or closed (and on manual dispatch), commits it to `docs/pr-review/` and
so publishes it at <https://forrt.org/replication-handbook/pr-review/>. Each run
covers all open PRs, and directories of merged or closed PRs are removed.

PRs from forks are skipped: their token cannot publish, and the renderer would
execute code from an untrusted branch. The book workflow (`publish.yml`) stashes
and restores `docs/pr-review/` so that rendering the book does not wipe it.

Chapters share one `libs/` directory of Quarto's JS and CSS, which keeps the
whole site around 2.5 MB rather than ~20 MB, so republishing it into the repo
stays cheap.

## Using it

- **PR pills** along the top switch between pull requests; the badge is the
  number of changes.
- **Chapters in this PR** in the sidebar lists the affected chapters only.
- **Next change** (or <kbd>n</kbd> / <kbd>p</kbd>) jumps from change to change and
  highlights the current one; the counter shows where you are.
- **deletions** unticked hides removed text, giving a clean read of the result.
- <kbd>←</kbd> / <kbd>→</kbd> switch chapter, <kbd>[</kbd> / <kbd>]</kbd> switch PR.
- The URL carries the PR and chapter (`#pr=42&ch=0`), so a view can be shared or
  bookmarked.

Serve over HTTP rather than opening `index.html` from disk: Chrome blocks some
`file://` iframe behaviour. `--serve` does this for you.

## How it works

1. `gh` supplies the open PRs; the base version of each changed `.qmd` comes from
   the merge base with `main`, the new version from the PR head.
2. `qmd_diff.py` unwraps the hard-wrapped Quarto source into logical units
   (paragraphs, headings, list items, tables, code blocks), diffs those, and then
   diffs words within a changed unit. Markdown constructs (citations, links,
   emphasis, shortcodes) are kept atomic so the marked-up source still parses.
   Changes separated by only a word or two are merged, so a rewritten sentence
   reads as one replacement instead of a dozen fragments.
3. The result is one merged `.qmd` per chapter with `[...]{.diff-ins}` /
   `[...]{.diff-del}` spans (`.diff-ins-block` / `.diff-del-block` divs for tables
   and code), rendered standalone by Quarto with the handbook theme, bibliography
   and CSL.
4. `assets/diff.css` and `assets/chapter_nav.js` are injected into each rendered
   chapter; `assets/shell.html` becomes `pr-review/index.html` with the build
   manifest inlined.

Because chapters render one at a time rather than as a book, cross-references to
other chapters (`@sec-…`) show up unresolved as **?@sec-…**, and links to other
chapters lead nowhere. Changes to `references.bib` and other non-`.qmd` files are
listed in the sidebar but not shown as tracked changes. Chapters that fail to render with code
execution are retried with `execute: enabled: false`.
