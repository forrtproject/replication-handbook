#!/usr/bin/env python3
"""Build a tracked-changes review site for the handbook's open pull requests.

For every PR it takes the chapters that the PR touches, merges the base and the
PR version of the source into one .qmd with the changes marked up, renders that
chapter with Quarto, and wraps everything in a single page with a PR switcher,
a chapter menu and a "jump to next change" button.

    python3 tools/pr-review/build_review.py            # all open PRs
    python3 tools/pr-review/build_review.py 42 35      # selected PRs
    python3 tools/pr-review/build_review.py --serve    # build, then serve + open

Requires: gh (authenticated), git, quarto, python3.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qmd_diff import diff_qmd  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ASSETS = HERE / "assets"
OUT = REPO / "pr-review"

# Files that a rendered chapter may need next to it.
SUPPORT = ["images", "data", "styles", "R", "_extensions", "theme.scss", "references.bib"]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


def sh(cmd, **kw):
    """Run a command, returning (ok, output)."""
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return p.returncode == 0, p.stdout + p.stderr


# --------------------------------------------------------------------------
# Talking to GitHub / git
# --------------------------------------------------------------------------


def list_prs(numbers):
    fields = "number,title,headRefName,baseRefName,url,author,updatedAt"
    if numbers:
        prs = [json.loads(run(["gh", "pr", "view", str(n), "--json", fields])) for n in numbers]
    else:
        prs = json.loads(run(["gh", "pr", "list", "--state", "open", "--limit", "50",
                              "--json", fields]))
    return sorted(prs, key=lambda p: p["number"], reverse=True)


def fetch_pr(pr):
    """Fetch the PR head and return (head_sha, base_sha)."""
    ref = f"refs/pr-review/{pr['number']}"
    run(["git", "fetch", "-f", "origin", f"pull/{pr['number']}/head:{ref}"], cwd=REPO)
    run(["git", "fetch", "origin", pr["baseRefName"]], cwd=REPO)
    head = run(["git", "rev-parse", ref], cwd=REPO).strip()
    base = run(["git", "merge-base", f"origin/{pr['baseRefName']}", head], cwd=REPO).strip()
    return head, base


def show(rev, path):
    ok, out = sh(["git", "show", f"{rev}:{path}"], cwd=REPO)
    return out if ok else ""


def changed_qmds(base, head):
    out = run(["git", "diff", "--name-only", base, head], cwd=REPO)
    return [f for f in out.split() if f.endswith(".qmd")]


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

FRONT_MATTER = """---
title: {title}
subtitle: "PR #{pr} · tracked changes"
bibliography: references.bib
csl: styles/apa.csl
filters:
  - fontawesome
format:
  html:
    theme: [cosmo, theme.scss]
    toc: true
    toc-depth: 3
    link-external-newwindow: true
    fig-cap-location: top
{extra}---
"""


def chapter_title(source, fallback):
    front = source.split("---")
    for chunk in front[:3]:
        m = re.search(r"^title:\s*(.+)$", chunk, re.M)
        if m:
            return m.group(1).strip().strip("\"'")
    return fallback


def tool_version():
    """Hash of the tool itself, so edits to it invalidate the build cache."""
    import hashlib

    h = hashlib.sha1()
    # shell.html is regenerated on every run, so it does not invalidate chapters
    for f in [HERE / "build_review.py", HERE / "qmd_diff.py",
              ASSETS / "diff.css", ASSETS / "chapter_nav.js"]:
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


def collect_assets(tmp, name, dest):
    """Move rendered assets into place, sharing the Quarto libraries site-wide.

    Every chapter ships the same bootstrap/quarto JS and CSS.  Keeping one copy
    in <site>/libs keeps the published site small enough to live in the repo.
    """
    files = tmp / f"{name}_files"
    if not files.is_dir():
        return
    libs = files / "libs"
    site_libs = dest.parent.parent / "libs"
    if libs.is_dir():
        for lib in libs.iterdir():
            target = site_libs / lib.name
            if not target.exists():
                shutil.copytree(lib, target)
        shutil.rmtree(libs)
    if any(files.iterdir()):
        target = dest.parent / files.name
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(files, target)


def build_chapter(pr, path, base, head, dest):
    """Diff one chapter, render it, and return its manifest entry (or None)."""
    old_src = show(base, path)
    new_src = show(head, path)
    if not new_src:
        return None  # file deleted by the PR
    merged, hunks = diff_qmd(old_src, new_src)
    title = chapter_title(new_src, Path(path).stem)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # Support files: directories from the working tree (images etc. rarely
        # differ), single files from the PR branch so citations match it.
        for item in SUPPORT:
            if (REPO / item).is_dir():
                shutil.copytree(REPO / item, tmp / item, dirs_exist_ok=True)
                continue
            content = show(head, item) or show("HEAD", item)
            if content:
                (tmp / item).write_text(content)

        name = Path(path).stem
        body = re.sub(r"^---\n.*?\n---\n", "", merged, count=1, flags=re.S)

        rendered = None
        for extra in ("", "execute:\n  enabled: false\n"):
            qmd = tmp / f"{name}.qmd"
            qmd.write_text(
                FRONT_MATTER.format(
                    title=json.dumps(title), pr=pr["number"], extra=extra
                )
                + body
            )
            ok, log = sh(["quarto", "render", qmd.name, "--to", "html"], cwd=tmp)
            if ok and (tmp / f"{name}.html").exists():
                rendered = (tmp / f"{name}.html").read_text()
                break
            last_log = log
        if rendered is None:
            print(f"    ! render failed for {path}:\n{last_log[-1500:]}", file=sys.stderr)
            return None

        dest.parent.mkdir(parents=True, exist_ok=True)
        collect_assets(tmp, name, dest)

    rendered = rendered.replace(f"{name}_files/libs/", "../libs/")
    dest.write_text(inject(rendered))
    return {
        "file": path,
        "title": title,
        "href": f"{pr['number']}/{Path(path).stem}.html",
        "hunks": hunks,
    }


def inject(html):
    """Add the tracked-changes styling and the in-page navigation script."""
    css = f"<style>\n{(ASSETS / 'diff.css').read_text()}\n</style>"
    js = f"<script>\n{(ASSETS / 'chapter_nav.js').read_text()}\n</script>"
    if "</head>" in html:
        html = html.replace("</head>", css + "\n</head>", 1)
    else:
        html = css + html
    if "</body>" in html:
        html = html.replace("</body>", js + "\n</body>", 1)
    else:
        html += js
    return html


# --------------------------------------------------------------------------


def main():
    global OUT
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prs", nargs="*", type=int, help="PR numbers (default: all open PRs)")
    ap.add_argument("--serve", action="store_true", help="serve the site and open a browser")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--clean", action="store_true", help="rebuild everything from scratch")
    ap.add_argument("--out", type=Path, default=OUT, help=f"output directory (default: {OUT})")
    args = ap.parse_args()
    OUT = args.out.resolve()

    if args.clean and OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    cache_path = OUT / ".cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    version = tool_version()
    manifest = []

    for pr in list_prs(args.prs):
        num = str(pr["number"])
        print(f"PR #{num}: {pr['title']}")
        head, base = fetch_pr(pr)
        files = changed_qmds(base, head)
        if not files:
            print("    (no .qmd changes, skipped)")
            continue

        cached = cache.get(num)
        if cached and cached["head"] == head and cached.get("tool") == version and all(
            (OUT / c["href"]).exists() for c in cached["entry"]["chapters"]
        ):
            print("    unchanged, reusing build")
            manifest.append(cached["entry"])
            continue

        chapters = []
        for path in files:
            print(f"    {path} ...", end="", flush=True)
            entry = build_chapter(pr, path, base, head, OUT / num / f"{Path(path).stem}.html")
            if entry:
                chapters.append(entry)
                print(f" {entry['hunks']} changes")
            else:
                print(" skipped")
        if not chapters:
            continue

        other = [f for f in run(["git", "diff", "--name-only", base, head], cwd=REPO).split()
                 if not f.endswith(".qmd")]
        entry = {
            "number": pr["number"],
            "title": pr["title"],
            "url": pr["url"],
            "author": pr.get("author", {}).get("login", ""),
            "updated": pr["updatedAt"][:10],
            "branch": pr["headRefName"],
            "chapters": chapters,
            "otherFiles": other,
        }
        manifest.append(entry)
        cache[num] = {"head": head, "tool": version, "entry": entry}
        cache_path.write_text(json.dumps(cache, indent=1))

    # drop directories of PRs that have since been merged or closed
    if not args.prs:
        live = {str(e["number"]) for e in manifest}
        for d in OUT.iterdir():
            if d.is_dir() and d.name.isdigit() and d.name not in live:
                shutil.rmtree(d)
                cache.pop(d.name, None)
        cache = {k: v for k, v in cache.items() if k in live}
        cache_path.write_text(json.dumps(cache, indent=1))

    shell = (ASSETS / "shell.html").read_text().replace(
        "/*__MANIFEST__*/null", json.dumps(manifest, indent=1)
    )
    (OUT / "index.html").write_text(shell)
    print(f"\nBuilt {len(manifest)} PR(s) → {OUT / 'index.html'}")

    if args.serve:
        os.chdir(OUT)
        url = f"http://localhost:{args.port}/index.html"
        print(f"Serving {url}  (Ctrl-C to stop)")
        webbrowser.open(url)
        subprocess.run([sys.executable, "-m", "http.server", str(args.port)])


if __name__ == "__main__":
    main()
