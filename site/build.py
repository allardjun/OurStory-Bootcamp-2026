#!/usr/bin/env python3
"""Build the OurStory site: the story, who wrote what, and the tree.

Reads story.md and the git history of this repository, and writes three static HTML pages into an output directory.
There are no third-party dependencies on purpose, so this runs on a bare GitHub Actions runner and in a Codespace without an install step.
"""

import argparse
import html
import os
import re
import subprocess
import sys
from pathlib import Path

# Hues are spaced around the colour wheel and assigned to authors in order of how many lines they wrote.
# Each page emits the hue as a CSS custom property, so the light and dark themes can pick their own lightness from the same hue.
HUES = [210, 25, 145, 320, 45, 265, 175, 0, 95, 240, 300, 65]

PAGES = [
    ("index.html", "The story"),
    ("blame.html", "Who wrote what"),
    ("tree.html", "The tree"),
]


def run(args, cwd=None):
    """Run a git command and return stdout, or None if it fails."""
    try:
        out = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout


def repo_url(root):
    """Work out the https URL of this repository, for linking commits and the network graph."""
    slug = os.environ.get("GITHUB_REPOSITORY")
    if not slug:
        remote = run(["git", "remote", "get-url", "origin"], cwd=root)
        if not remote:
            return None
        remote = remote.strip()
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
        if not m:
            return None
        slug = m.group(1)
    return f"https://github.com/{slug}"


# --- reading the story -------------------------------------------------------


class Line:
    """One line of story.md, keeping the file line number so it matches what GitHub's editor shows."""

    def __init__(self, fileno, text):
        self.fileno = fileno
        self.text = text
        self.author = None
        self.sha = None


def read_story(path):
    """Split story.md into a title, a byline, and the numbered lines of the story itself."""
    raw = path.read_text(encoding="utf-8").split("\n")
    if raw and raw[-1] == "":
        raw.pop()

    # A story marked as verse keeps every line break, because in a poem the line break is the form rather than sentence wrapping.
    # Prose is reflowed into paragraphs on the story page, so that source written one-sentence-per-line reads as ordinary prose once published.
    # The marker sits at the end of the file, away from the first dozen lines where students overwhelmingly edit.
    verse = "<!-- verse -->" in "\n".join(raw)

    title, byline, body = None, None, []
    for i, text in enumerate(raw, start=1):
        stripped = text.strip()
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue
        if title is None and stripped.startswith("# "):
            title = stripped[2:].strip()
            continue
        # The byline is the first italic line after the title; blank lines in between do not count as story content yet.
        if byline is None and not any(l.text.strip() for l in body) and re.fullmatch(r"[_*].+[_*]", stripped):
            byline = stripped[1:-1].strip()
            continue
        body.append(Line(i, text))

    # Trim blank lines from each end so the page does not open or close with a gap.
    while body and not body[0].text.strip():
        body.pop(0)
    while body and not body[-1].text.strip():
        body.pop()

    return title or "Our story", byline, body, verse


def inline(text):
    """Escape HTML, then honour the small amount of Markdown a story actually uses."""
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\w)[*_](.+?)[*_](?!\w)", r"<em>\1</em>", out)
    out = out.replace("---", "&mdash;").replace("--", "&ndash;")
    return out


# --- reading the history -----------------------------------------------------


def blame(root, relpath, lines):
    """Attach an author and commit to each line, using git blame."""
    out = run(["git", "blame", "--line-porcelain", "--", relpath], cwd=root)
    if not out:
        return False

    by_fileno = {}
    sha = author = None
    for entry in out.split("\n"):
        m = re.match(r"^([0-9a-f]{40}) \d+ (\d+)", entry)
        if m:
            sha, lineno = m.group(1), int(m.group(2))
            continue
        if entry.startswith("author "):
            author = entry[len("author "):].strip()
            continue
        if entry.startswith("\t") and sha is not None:
            by_fileno[lineno] = (author or "unknown", sha)
            sha = author = None

    for line in lines:
        if line.fileno in by_fileno:
            line.author, line.sha = by_fileno[line.fileno]
    return True


def author_colors(root, lines):
    """Assign each author a stable hue.

    Authors who still have surviving lines are coloured first, in order of how many they wrote, so the busiest colours are the most distinct.
    Everyone else who ever committed is then given a colour too, because losing a line to a merge conflict should not make you invisible on the tree page.
    """
    counts = {}
    for line in lines:
        if line.author and line.text.strip():
            counts[line.author] = counts.get(line.author, 0) + 1
    ordered = sorted(counts, key=lambda a: (-counts[a], a))

    colors = {a: HUES[i % len(HUES)] for i, a in enumerate(ordered)}
    log = run(["git", "log", "--all", "--format=%an"], cwd=root) or ""
    for author in dict.fromkeys(log.split("\n")):
        if author and author not in colors:
            colors[author] = HUES[len(colors) % len(HUES)]
    return colors, counts, ordered


# --- rendering ---------------------------------------------------------------

CSS = """
:root {
  --bg: #fbfaf8; --fg: #1b1a18; --dim: #6c6862; --rule: #e2ded7;
  --card: #ffffff; --accent-l: 45%; --tint: 0.13;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #16151a; --fg: #ece9e4; --dim: #9a948c; --rule: #302e35;
    --card: #1d1c22; --accent-l: 72%; --tint: 0.20;
  }
}
:root[data-theme="dark"] {
  --bg: #16151a; --fg: #ece9e4; --dim: #9a948c; --rule: #302e35;
  --card: #1d1c22; --accent-l: 72%; --tint: 0.20;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 20px/1.65 ui-serif, Georgia, "Iowan Old Style", serif;
  -webkit-text-size-adjust: 100%;
}
.wrap { max-width: 52rem; margin: 0 auto; padding: 2rem 1.25rem 5rem; }
.wrap.wide { max-width: min(1800px, 96vw); }
header { border-bottom: 1px solid var(--rule); margin-bottom: 2rem; }
.instance {
  font: 600 0.7rem/1 ui-sans-serif, system-ui, sans-serif;
  letter-spacing: 0.12em; text-transform: uppercase; color: var(--dim);
}
h1 { font-size: clamp(2rem, 5vw, 3rem); line-height: 1.1; margin: 0.6rem 0 0.3rem; }
.byline { color: var(--dim); font-style: italic; margin: 0 0 1.2rem; }
nav { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0 0 1.25rem; }
nav a {
  font: 600 0.85rem/1 ui-sans-serif, system-ui, sans-serif;
  text-decoration: none; color: var(--dim);
  padding: 0.5rem 0.85rem; border: 1px solid var(--rule); border-radius: 99px;
}
nav a[aria-current] { color: var(--bg); background: var(--fg); border-color: var(--fg); }
.note {
  font: 0.85rem/1.5 ui-sans-serif, system-ui, sans-serif; color: var(--dim);
  background: var(--card); border: 1px solid var(--rule); border-radius: 10px;
  padding: 0.75rem 1rem; margin: 0 0 1.75rem;
}
.note code { font-size: 0.95em; }

/* The story as something to read. Prose reflows into paragraphs; verse keeps its own line breaks. */
.read p { margin: 0 0 1.15rem; }
.read.verse p { margin: 0 0 1.6rem; }
.read.verse .v { text-indent: 0; }
.read p:last-child { margin-bottom: 0; }

/* The story as a list of lines, with a gutter that matches GitHub's editor. */
.story { display: grid; grid-template-columns: 3.2rem 1fr; row-gap: 0.15rem; }
.n {
  font: 0.72rem/1.75 ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--dim); text-align: right; padding-right: 1rem;
  -webkit-user-select: none; user-select: none;
}
.t { min-width: 0; overflow-wrap: break-word; }
.gap { height: 0.9rem; grid-column: 1 / -1; }
.hot { background: color-mix(in srgb, var(--fg) 6%, transparent); }

/* Blame view: each line tinted by its author's hue. */
.story.blamed .t {
  background: hsl(var(--h) 70% 50% / var(--tint));
  border-left: 3px solid hsl(var(--h) 65% var(--accent-l));
  padding: 0.05rem 0.5rem; border-radius: 0 4px 4px 0;
}
.story.blamed .t.empty { background: none; border-left-color: transparent; }

.legend { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0 0 2rem; }
.who {
  display: inline-flex; align-items: baseline; gap: 0.45rem;
  font: 0.85rem/1 ui-sans-serif, system-ui, sans-serif;
  border: 1px solid var(--rule); border-radius: 99px; padding: 0.45rem 0.8rem;
  background: hsl(var(--h) 70% 50% / var(--tint));
}
.who b { font-weight: 600; color: hsl(var(--h) 65% var(--accent-l)); }
.who span { color: var(--dim); font-variant-numeric: tabular-nums; }

/* Tree view: a wide graph that scrolls on its own rather than stretching the page. */
.tree { overflow-x: auto; background: var(--card); border: 1px solid var(--rule); border-radius: 10px; padding: 1rem; }

/* The Graphviz drawing. Graphviz passes our class names through to the SVG, so the fills come from the page palette and follow the light and dark themes. */
.gv svg { display: block; max-width: 100%; height: auto; }
.gv .e > path { stroke: var(--dim); opacity: 0.55; }
.gv .merge > path { stroke: var(--dim); opacity: 0.9; }
.gv text { font-weight: 600; }
.gv a:hover text { text-decoration: underline; }

details.fold { margin-top: 1.25rem; }
details.fold > summary {
  cursor: pointer; color: var(--dim);
  font: 600 0.85rem/1 ui-sans-serif, system-ui, sans-serif;
  padding: 0.5rem 0; list-style-position: inside;
}
details.fold > summary:hover { color: var(--fg); }
details.fold[open] > summary { margin-bottom: 0.6rem; }
.tree pre {
  margin: 0; font: 0.8rem/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
  white-space: pre;
}
.tree .g { color: var(--dim); }
.tree .h { color: var(--dim); }
.tree .h a { color: inherit; }
.tree .a { color: hsl(var(--h) 65% var(--accent-l)); font-weight: 600; }
.tree .s { color: var(--fg); }
footer {
  margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--rule);
  font: 0.8rem/1.6 ui-sans-serif, system-ui, sans-serif; color: var(--dim);
}
a { color: inherit; }
"""


def shell(page, title, instance, heading, byline, body, links, wide=False):
    """Wrap page content in the shared chrome."""
    cls = " wide" if wide else ""
    # Built without escaped quotes inside the f-string expression, which older Python versions reject.
    current = ' aria-current="page"'
    nav = "".join(
        '<a href="{}"{}>{}</a>'.format(href, current if href == page else "", html.escape(label))
        for href, label in PAGES
    )
    sub = f'<p class="byline">{inline(byline)}</p>' if byline else ""
    inst = f'<p class="instance">{html.escape(instance)}</p>' if instance else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap{cls}">
<header>{inst}<h1>{html.escape(heading)}</h1>{sub}<nav>{nav}</nav></header>
{body}
<footer>{links}</footer>
</div>
</body>
</html>
"""


def render_story(lines, blamed, colors, hot):
    """Render the numbered story, optionally tinted by author."""
    out = [f'<div class="story{" blamed" if blamed else ""}">']
    prev_blank = False
    for line in lines:
        if not line.text.strip():
            if not prev_blank:
                out.append('<div class="gap"></div>')
            prev_blank = True
            continue
        prev_blank = False
        style = ""
        if blamed and line.author in colors:
            style = f' style="--h:{colors[line.author]}"'
        title = f' title="{html.escape(line.author)}"' if blamed and line.author else ""
        klass = "t hot" if (hot and line.fileno <= hot) else "t"
        out.append(f'<div class="n">{line.fileno}</div>')
        out.append(f'<div class="{klass}"{style}{title}>{inline(line.text)}</div>')
    out.append("</div>")
    return "\n".join(out)


def render_reading(lines, verse):
    """Render the story as something to read, rather than as a list of lines.

    Prose is reflowed: the source is written one sentence per line, and those sentences join back into a paragraph here, which is what a reader expects to see.
    Verse keeps every line exactly where the poet put it.
    Blank lines separate paragraphs in both cases.
    """
    blocks, current = [], []
    for line in lines:
        if line.text.strip():
            current.append(line.text.strip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)

    out = []
    for block in blocks:
        if verse:
            out.append('<p class="v">' + "<br>\n".join(inline(t) for t in block) + "</p>")
        else:
            out.append("<p>" + inline(" ".join(block)) + "</p>")
    return f'<div class="read{" verse" if verse else ""}">' + "\n".join(out) + "</div>"


def render_legend(colors, counts, ordered):
    if not ordered:
        return ""
    chips = "".join(
        f'<span class="who" style="--h:{colors[a]}"><b>{html.escape(a)}</b>'
        f'<span>{counts[a]} line{"s" if counts[a] != 1 else ""}</span></span>'
        for a in ordered
    )
    return f'<div class="legend">{chips}</div>'


def render_tree(root, colors, url):
    """Render git log --graph as HTML, colouring author names to match the blame page."""
    sep = "\x1f"
    out = run(
        ["git", "log", "--graph", "--all", "--date-order", "--date=short",
         f"--pretty=format:%h{sep}%an{sep}%ad{sep}%s"],
        cwd=root,
    )
    if not out:
        return '<div class="note">No history to draw yet.</div>'

    rows = []
    for raw in out.split("\n"):
        if sep not in raw:
            rows.append(f'<span class="g">{html.escape(raw)}</span>')
            continue
        parts = raw.split(sep)
        # parts[0] is the graph prefix glued to the short hash.
        prefix, sha = parts[0][:-7], parts[0][-7:]
        author, date, subject = parts[1], parts[2], sep.join(parts[3:])
        hue = colors.get(author, 220)
        link = f'<a href="{url}/commit/{sha}">{sha}</a>' if url else sha
        rows.append(
            f'<span class="g">{html.escape(prefix)}</span>'
            f'<span class="h">{link}</span> '
            f'<span class="a" style="--h:{hue}">{html.escape(author)}</span> '
            f'<span class="g">{html.escape(date)}</span>  '
            f'<span class="s">{html.escape(subject)}</span>'
        )
    return '<div class="tree"><pre>' + "\n".join(rows) + "</pre></div>"


def hsl_hex(h, s, l):
    """Convert an HSL colour to a hex string, for standalone images that have no stylesheet to inherit from."""
    import colorsys
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def commit_graph(root):
    """Read the commit DAG: one entry per commit, with its parents."""
    sep = "\x1f"
    out = run(
        ["git", "log", "--all", "--date-order", "--date=short",
         f"--pretty=format:%H{sep}%P{sep}%an{sep}%ad{sep}%s"],
        cwd=root,
    )
    if not out:
        return []

    commits = []
    for raw in out.split("\n"):
        parts = raw.split(sep)
        if len(parts) < 5:
            continue
        sha, parents, author, date, subject = parts[0], parts[1], parts[2], parts[3], sep.join(parts[4:])
        commits.append({
            "sha": sha,
            "parents": [p for p in parents.split() if p],
            "author": author,
            "date": date,
            "subject": subject,
        })
    return commits


def build_dot(commits, colors, url):
    """Write the commit DAG as Graphviz DOT.

    Each commit becomes a node carrying a CSS class rather than a baked-in colour, so that the page's light and dark palettes can drive the fills.
    Edges run from a commit to each of its parents, which is what draws a merge as a join of two lines.
    """
    hues = {}
    for c in commits:
        hues.setdefault(c["author"], colors.get(c["author"], 220))
    index = {a: i for i, a in enumerate(hues)}

    lines = [
        "digraph story {",
        '  bgcolor="transparent";',
        "  rankdir=RL;",   # edges point from a commit to its parent, so RL puts the oldest commit on the left and time runs left to right
        '  node [shape=box, style="filled,rounded", fontname="Helvetica,Arial,sans-serif",'
        ' fontsize=16, penwidth=1.4, margin="0.12,0.06", height=0.3];',
        '  edge [arrowhead=none, penwidth=1.4];',
        "  nodesep=0.18;",
        "  ranksep=0.5;",
    ]

    known = {c["sha"] for c in commits}
    for c in commits:
        short = c["sha"][:7]
        tooltip = f'{short}  {c["subject"]}'.replace('"', "'")
        merge = len(c["parents"]) > 1
        attrs = [
            f'tooltip="{tooltip}"',
            f'class="c a{index[c["author"]]}"',
        ]
        if merge:
            # A merge is drawn as a small junction dot rather than a labelled box.
            # In this activity the instructor merges every pull request, so labelling all of them would fill the picture with the same name twenty times and squeeze everyone else out.
            attrs += ['label=""', "shape=circle", "width=0.16", "height=0.16", "fixedsize=true"]
        else:
            label = c["author"].replace('"', "'")
            attrs.insert(0, 'label="' + label + '"')
        if url:
            attrs.append(f'URL="{url}/commit/{c["sha"]}"')
            attrs.append('target="_blank"')
        lines.append(f'  "{c["sha"]}" [{", ".join(attrs)}];')

    for c in commits:
        for p in c["parents"]:
            if p in known:
                # A commit with more than one parent is a merge; mark those edges so they can be styled apart.
                klass = "e merge" if len(c["parents"]) > 1 else "e"
                lines.append(f'  "{c["sha"]}" -> "{p}" [class="{klass}"];')

    lines.append("}")
    return "\n".join(lines), hues, index


def render_tree_svg(root, colors, url):
    """Render the commit DAG as an inline SVG using Graphviz, or return None if dot is unavailable."""
    commits = commit_graph(root)
    if not commits:
        return None

    dot_src, hues, index = build_dot(commits, colors, url)
    try:
        proc = subprocess.run(["dot", "-Tsvg"], input=dot_src,
                              capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    svg = proc.stdout
    # Drop the XML preamble and the DOCTYPE so the SVG can be inlined in HTML.
    svg = svg[svg.index("<svg"):] if "<svg" in svg else svg
    # Let the SVG scale to the width of its container rather than its natural pixel size.
    svg = re.sub(r'<svg width="\d+pt" height="\d+pt"', '<svg', svg, count=1)

    # One rule per author, keyed on the class Graphviz passed through.
    rules = "\n".join(
        f'.gv .a{i} > polygon, .gv .a{i} > ellipse, .gv .a{i} > path {{ fill: hsl({hues[a]} 70% 50% / var(--tint));'
        f' stroke: hsl({hues[a]} 65% var(--accent-l)); }}\n'
        f'.gv .a{i} text {{ fill: hsl({hues[a]} 65% var(--accent-l)); }}'
        for a, i in index.items()
    )
    return f'<style>{rules}</style><div class="tree gv">{svg}</div>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--story", default="story.md")
    ap.add_argument("--out", default="_site")
    ap.add_argument("--hot", type=int, default=0,
                    help="highlight file lines up to this number as the suggested editing zone")
    ap.add_argument("--dot", action="store_true",
                    help="print the commit graph as Graphviz DOT and exit, instead of building the site")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    story_path = root / args.story
    if not story_path.exists():
        sys.exit(f"{story_path} not found")

    instance_file = root / "instance.txt"
    instance = instance_file.read_text(encoding="utf-8").strip() if instance_file.exists() else ""

    title, byline, lines, verse = read_story(story_path)
    blamed = blame(root, args.story, lines)
    colors, counts, ordered = author_colors(root, lines)
    url = repo_url(root)

    if args.dot:
        # Used by scripts/tree-image.sh so the standalone image and the web page are drawn from exactly the same graph.
        commits = commit_graph(root)
        if not commits:
            sys.exit("no history to draw yet")
        dot_src, hues, index = build_dot(commits, colors, url)
        # Standalone images have no stylesheet behind them, so bake the colours in.
        baked = []
        for line in dot_src.split("\n"):
            m = re.search(r'class="c a(\d+)"', line)
            if m:
                hue = list(hues.values())[int(m.group(1))]
                line = line.replace(
                    f'class="c a{m.group(1)}"',
                    f'color="{hsl_hex(hue, 0.65, 0.45)}", fillcolor="{hsl_hex(hue, 0.70, 0.92)}",'
                    f' fontcolor="{hsl_hex(hue, 0.65, 0.32)}"')
            baked.append(line)
        print("\n".join(baked))
        return

    out_dir = root / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    edit = f'<a href="{url}/edit/main/{args.story}">edit the story</a> &middot; ' if url else ""
    links = f'{edit}built from <code>{html.escape(args.story)}</code> by GitHub Actions'

    hot_note = ""
    if args.hot:
        hot_note = (f'<div class="note">The shaded lines are today’s editing zone: '
                    f'pick a number between the first line and <b>{args.hot}</b>. '
                    f'The numbers on the left are the same ones GitHub shows you in its editor.</div>')

    (out_dir / "index.html").write_text(
        shell("index.html", title, instance, title, byline,
              hot_note + (render_story(lines, False, colors, args.hot)
                          if args.hot else render_reading(lines, verse)), links),
        encoding="utf-8")

    if blamed:
        body = render_legend(colors, counts, ordered) + render_story(lines, True, colors, 0)
    else:
        body = '<div class="note">No git history for this file yet.</div>'
    (out_dir / "blame.html").write_text(
        shell("blame.html", f"Who wrote what — {title}", instance,
              "Who wrote what", "Every line is coloured by the person who last changed it.",
              body, links),
        encoding="utf-8")

    net = f'<a href="{url}/network">the fork network</a> &middot; ' if url else ""
    ascii_tree = render_tree(root, colors, url)
    svg_tree = render_tree_svg(root, colors, url)
    if svg_tree:
        # The picture first, with the terminal version folded away underneath.
        # They are the same history drawn two ways, which is the bridge to the Codespace track.
        tree_body = (svg_tree +
                     '<details class="fold"><summary>Show the terminal version</summary>'
                     + ascii_tree + "</details>")
    else:
        tree_body = ascii_tree

    (out_dir / "tree.html").write_text(
        shell("tree.html", f"The tree — {title}", instance,
              "The tree", "Every commit, and every merge that brought them together.",
              tree_body, net + links, wide=True),
        encoding="utf-8")

    print(f"wrote {out_dir}/index.html, blame.html, tree.html "
          f"({len(lines)} lines, {len(ordered)} author(s))")


if __name__ == "__main__":
    main()
