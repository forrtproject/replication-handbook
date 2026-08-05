"""Semantic word-level diff between two versions of a Quarto (.qmd) source file.

The output is a single merged .qmd whose changed passages are wrapped in pandoc
spans/divs (``.diff-ins`` / ``.diff-del``), so the rendered HTML shows the
change like tracked changes in a word processor.

The handbook sources are hard-wrapped by the Quarto visual editor, so a plain
line diff would flag whole paragraphs whenever a sentence is re-wrapped.  We
therefore unwrap the source into logical units (paragraph, heading, list item,
table, code block, ...) first, diff those, and only then diff words inside a
changed unit.
"""

import re
from difflib import SequenceMatcher

# --------------------------------------------------------------------------
# Parsing the source into logical units
# --------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6}\s+)(.*)$")
LIST_RE = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)(.*)$")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
DIV_RE = re.compile(r"^\s*:::+")
TABLE_RE = re.compile(r"^\s*(\|.*|[+|][-=+| :]+)$")
YAML_RE = re.compile(r"^---\s*$")


class Unit:
    """One logical chunk of markdown source."""

    __slots__ = ("kind", "prefix", "text", "raw")

    def __init__(self, kind, prefix, text, raw):
        self.kind = kind  # para | heading | list | table | code | fence | blank
        self.prefix = prefix  # structural markup kept outside the diff spans
        self.text = text  # the prose that gets word-diffed
        self.raw = raw  # original lines, used verbatim for unchanged units

    @property
    def key(self):
        return re.sub(r"\s+", " ", self.text).strip()

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"Unit({self.kind}, {self.key[:40]!r})"


def split_front_matter(source):
    """Return (front_matter_lines, body_lines)."""
    lines = source.splitlines()
    if lines and YAML_RE.match(lines[0]):
        for i in range(1, len(lines)):
            if YAML_RE.match(lines[i]):
                return lines[: i + 1], lines[i + 1 :]
    return [], lines


def parse_units(lines):
    units = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        if not line.strip():
            units.append(Unit("blank", "", "", [line]))
            i += 1
            continue

        fence = FENCE_RE.match(line)
        if fence:  # fenced code block, kept intact
            marker = fence.group(1)
            block = [line]
            i += 1
            while i < n:
                block.append(lines[i])
                if lines[i].strip().startswith(marker):
                    i += 1
                    break
                i += 1
            units.append(Unit("code", "", "\n".join(block), block))
            continue

        if DIV_RE.match(line):  # ::: fences are structure, never marked up
            units.append(Unit("fence", "", line.strip(), [line]))
            i += 1
            continue

        if TABLE_RE.match(line):
            block = []
            while i < n and TABLE_RE.match(lines[i]):
                block.append(lines[i])
                i += 1
            units.append(Unit("table", "", "\n".join(block), block))
            continue

        heading = HEADING_RE.match(line)
        if heading:
            units.append(Unit("heading", heading.group(1), heading.group(2), [line]))
            i += 1
            continue

        item = LIST_RE.match(line)
        if item:
            raw = [line]
            text = [item.group(2)]
            indent = len(item.group(1))
            i += 1
            while i < n:
                nxt = lines[i]
                if (
                    not nxt.strip()
                    or LIST_RE.match(nxt)
                    or HEADING_RE.match(nxt)
                    or DIV_RE.match(nxt)
                    or FENCE_RE.match(nxt)
                    or len(nxt) - len(nxt.lstrip()) < indent - 1
                ):
                    break
                raw.append(nxt)
                text.append(nxt.strip())
                i += 1
            units.append(Unit("list", item.group(1), " ".join(text), raw))
            continue

        # plain paragraph: join the hard-wrapped lines
        raw = []
        text = []
        while i < n:
            nxt = lines[i]
            if (
                not nxt.strip()
                or LIST_RE.match(nxt)
                or HEADING_RE.match(nxt)
                or DIV_RE.match(nxt)
                or FENCE_RE.match(nxt)
                or TABLE_RE.match(nxt)
            ):
                break
            raw.append(nxt)
            text.append(nxt.strip())
            i += 1
        units.append(Unit("para", "", " ".join(text), raw))
    return units


# --------------------------------------------------------------------------
# Word-level diff inside a unit
# --------------------------------------------------------------------------

# Constructs that must never be split in the middle, or the markdown breaks.
ATOMIC = re.compile(
    r"""
      \[[^\]\[]*\]\([^)\s]*(?:\s+"[^"]*")?\)   # [text](url)
    | \[[^\]\[]*\]\{[^}]*\}                    # [text]{.class}
    | \[[^\]\[]*\]                             # [@citation], [^fn]
    | !\[[^\]\[]*\]\([^)]*\)                   # images
    | \{\{<[^>]*>\}\}                          # shortcodes
    | `[^`]*`                                  # inline code
    | \*\*[^*]+\*\*                            # bold
    | \*[^*\s][^*]*\*                          # italics
    | \$[^$]+\$                                # inline math
    | @[\w:.#$%&+?<>~/-]+                      # bare citations
    | \S+                                      # anything else
    """,
    re.VERBOSE,
)


def tokenize(text):
    """Split into words, keeping markdown constructs and whitespace."""
    tokens = []
    pos = 0
    for match in ATOMIC.finditer(text):
        if match.start() > pos:
            tokens.append(text[pos : match.start()])
        tokens.append(match.group(0))
        pos = match.end()
    if pos < len(text):
        tokens.append(text[pos:])
    return tokens


def _balanced(text):
    return (
        text.count("[") == text.count("]")
        and text.count("(") == text.count(")")
        and text.count("`") % 2 == 0
        and text.count("$") % 2 == 0
    )


def span(text, cls, hunk):
    """Wrap text in a pandoc span, falling back to plain text if unsafe."""
    stripped = text.strip()
    if not stripped:
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()) :]
    if not _balanced(stripped):
        return text
    return f'{lead}[{stripped}]{{.{cls} data-hunk="{hunk}"}}{trail}'


MIN_EQUAL_RUN = 4  # words that must survive between two edits to keep them apart


def coalesce(opcodes, a, b):
    """Merge edits separated by only a word or two, so rewrites read as one change.

    Without this a rewritten sentence shows up as a dozen interleaved
    insert/delete fragments that are harder to read than the rewrite itself.
    """
    out = []
    for op in opcodes:
        tag, i1, i2, j1, j2 = op
        if (
            tag == "equal"
            and out
            and len([t for t in a[i1:i2] if t.strip()]) < MIN_EQUAL_RUN
        ):
            out.append(("replace", i1, i2, j1, j2))
            continue
        out.append(op)

    merged = []
    for tag, i1, i2, j1, j2 in out:
        if merged and tag != "equal" and merged[-1][0] != "equal":
            p = merged[-1]
            merged[-1] = ("replace", p[1], i2, p[3], j2)
        else:
            merged.append((tag, i1, i2, j1, j2))
    # a "replace" that turns out to have an empty side is really an insert/delete
    return [
        ("delete" if j1 == j2 else "insert" if i1 == i2 else tag, i1, i2, j1, j2)
        if tag == "replace"
        else (tag, i1, i2, j1, j2)
        for tag, i1, i2, j1, j2 in merged
    ]


def merge_inline(old_text, new_text, hunk):
    """Merge two versions of one unit into marked-up markdown."""
    a, b = tokenize(old_text), tokenize(new_text)
    matcher = SequenceMatcher(a=a, b=b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in coalesce(matcher.get_opcodes(), a, b):
        if tag == "equal":
            out.append("".join(b[j1:j2]))
        else:
            if tag in ("delete", "replace"):
                out.append(span("".join(a[i1:i2]), "diff-del", hunk))
            if tag in ("insert", "replace"):
                out.append(span("".join(b[j1:j2]), "diff-ins", hunk))
    return "".join(out)


# --------------------------------------------------------------------------
# Assembling the merged document
# --------------------------------------------------------------------------


def _mark_unit(unit, cls, hunk):
    """Render a wholly added/removed unit with its markup preserved."""
    if unit.kind in ("code", "table"):
        return [f'::: {{.{cls}-block data-hunk="{hunk}"}}', unit.text, ":::"]
    if unit.kind == "fence":
        return [unit.text] if cls == "diff-ins" else []
    if unit.kind == "blank":
        return list(unit.raw)
    body = span(unit.text, cls, hunk)
    if unit.kind == "list":
        return [unit.prefix + body]
    return [unit.prefix + body]


def _pair(old_units, new_units):
    """Greedily pair up units of a replace hunk that are revisions of each other."""
    pairs = []
    i = j = 0
    while i < len(old_units) and j < len(new_units):
        a, b = old_units[i], new_units[j]
        if a.kind == b.kind and SequenceMatcher(a=a.key, b=b.key).ratio() >= 0.4:
            pairs.append((a, b))
            i += 1
            j += 1
            continue
        # look one step ahead on either side before giving up on a pairing
        ahead_new = (
            j + 1 < len(new_units)
            and a.kind == new_units[j + 1].kind
            and SequenceMatcher(a=a.key, b=new_units[j + 1].key).ratio() >= 0.6
        )
        if ahead_new:
            pairs.append((None, b))
            j += 1
            continue
        pairs.append((a, None))
        i += 1
    pairs.extend((u, None) for u in old_units[i:])
    pairs.extend((None, u) for u in new_units[j:])
    return pairs


def diff_qmd(old_source, new_source):
    """Return (merged_source, n_hunks) for two versions of a .qmd file."""
    front, new_body = split_front_matter(new_source)
    _, old_body = split_front_matter(old_source)

    old_units = parse_units(old_body)
    new_units = parse_units(new_body)

    matcher = SequenceMatcher(
        a=[u.key for u in old_units], b=[u.key for u in new_units], autojunk=False
    )

    out = list(front)
    hunk = 0

    def emit_pair(a, b):
        nonlocal hunk
        if a is not None and b is not None:
            if a.key == b.key:
                out.extend(b.raw)
                return
            hunk += 1
            if a.kind == b.kind and a.kind not in ("code", "table", "fence", "blank"):
                out.append(a.prefix + merge_inline(a.text, b.text, hunk))
            else:
                out.extend(_mark_unit(a, "diff-del", hunk))
                out.extend(_mark_unit(b, "diff-ins", hunk))
        elif a is not None:
            if a.kind == "blank":
                return
            hunk += 1
            out.extend(_mark_unit(a, "diff-del", hunk))
        elif b is not None:
            if b.kind == "blank":
                out.extend(b.raw)
                return
            hunk += 1
            out.extend(_mark_unit(b, "diff-ins", hunk))

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for u in new_units[j1:j2]:
                out.extend(u.raw)
        elif tag == "delete":
            for u in old_units[i1:i2]:
                emit_pair(u, None)
        elif tag == "insert":
            for u in new_units[j1:j2]:
                emit_pair(None, u)
        else:
            olds = [u for u in old_units[i1:i2] if u.kind != "blank"]
            news = [u for u in new_units[j1:j2] if u.kind != "blank"]
            for a, b in _pair(olds, news):
                emit_pair(a, b)
                out.append("")

    # collapse runs of blank lines introduced by the marking above
    cleaned = []
    for line in out:
        if not line.strip() and cleaned and not cleaned[-1].strip():
            continue
        cleaned.append(line)
    return "\n".join(cleaned) + "\n", hunk
