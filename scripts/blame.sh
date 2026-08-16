#!/usr/bin/env bash
#
# Show who wrote each line of the story, coloured by author, in the terminal.
#
#   ./scripts/blame.sh
#
# The website version of this is nicer to project; this one is for showing that the same information comes straight out of git.

set -euo pipefail
STORY="${1:-story.md}"

git blame --line-porcelain -- "$STORY" | python3 -c '
import re, sys

COLORS = [39, 208, 41, 201, 220, 141, 44, 196, 118, 33, 213, 190]
lines, sha, author = [], None, None

for entry in sys.stdin.read().split("\n"):
    m = re.match(r"^([0-9a-f]{40}) \d+ (\d+)", entry)
    if m:
        sha = m.group(1)[:7]
        continue
    if entry.startswith("author "):
        author = entry[7:].strip()
        continue
    if entry.startswith("\t"):
        lines.append((sha, author, entry[1:]))
        sha = author = None

counts = {}
for _, a, text in lines:
    if text.strip():
        counts[a] = counts.get(a, 0) + 1
order = sorted(counts, key=lambda a: (-counts[a], a))
color = {a: COLORS[i % len(COLORS)] for i, a in enumerate(order)}
width = max((len(a) for a in counts), default=0)

for sha, a, text in lines:
    if not text.strip():
        print()
        continue
    c = color.get(a, 244)
    print(f"\033[38;5;{c}m{a:<{width}}\033[0m \033[2m{sha}\033[0m  {text}")

print()
for a in order:
    print(f"\033[38;5;{color[a]}m██\033[0m {a} — {counts[a]} line" + ("s" if counts[a] != 1 else ""))
'
