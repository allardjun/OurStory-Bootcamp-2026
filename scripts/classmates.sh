#!/usr/bin/env bash
#
# Pull every classmate's copy into this one, so that `git log --graph` shows the whole class at once.
#
#   ./scripts/classmates.sh          add everyone who forked, and fetch their work
#   ./scripts/classmates.sh --list   just show who forked, and who forked from whom
#
# Each fork becomes a git "remote" named after its owner, so afterwards you can do things like:
#
#   ./scripts/tree.sh                the whole class as one picture
#   git diff main alice/main         what did alice change?
#
# This works in a Codespace with no setup: the GitHub CLI is already installed and already signed in there.
# It also works anywhere else, because the fork list of a public repository can be read without signing in at all.
#
# It walks the whole fork tree, not just the first level. That matters here: Group B forks from Group A, so half the class are forks of forks and do not appear in the original's own fork list.

set -euo pipefail

ORIGIN="$(git remote get-url origin)"
SLUG="$(printf '%s' "$ORIGIN" | sed -E 's#.*github\.com[:/]##; s#\.git$##')"
MODE="${1:-}"

# Prefer the GitHub CLI when it is signed in, because it has a much higher rate limit than anonymous requests.
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  FETCHER=gh
else
  FETCHER=curl
fi

export SLUG MODE FETCHER
python3 <<'PY'
import json, os, subprocess, sys
from collections import deque

SLUG, MODE, FETCHER = os.environ["SLUG"], os.environ["MODE"], os.environ["FETCHER"]


def api(path):
    if FETCHER == "gh":
        cmd = ["gh", "api", path]
    else:
        cmd = ["curl", "-fsSL", f"https://api.github.com/{path}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        return json.loads(out)
    except Exception:
        return None


# Walk up to the original, in case we are ourselves somebody's fork.
root = SLUG
while True:
    info = api(f"repos/{root}")
    parent = (info or {}).get("parent")
    if not parent:
        break
    root = parent["full_name"]

print(f"This copy:     {SLUG}")
print(f"The original:  {root}")
print()

# Walk down the whole fork tree, breadth first.
found, seen, queue = [], {root}, deque([(root, 0)])
while queue:
    repo, depth = queue.popleft()
    if depth > 3:
        continue
    forks = api(f"repos/{repo}/forks?per_page=100")
    if not isinstance(forks, list):
        continue
    for f in forks:
        full = f["full_name"]
        if full in seen:
            continue
        seen.add(full)
        found.append((f["owner"]["login"], full, f["clone_url"], depth + 1, repo))
        queue.append((full, depth + 1))

if not found:
    print(f"Nobody has forked {root} yet.")
    sys.exit(0)

if MODE == "--list":
    for owner, full, _, depth, parent in found:
        print("  " + "    " * (depth - 1) + full + ("" if depth == 1 else f"   (from {parent})"))
    print()
    direct = sum(1 for f in found if f[3] == 1)
    print(f"{len(found)} copies: {direct} from the original, {len(found) - direct} from a classmate.")
    sys.exit(0)

added = 0
for owner, full, url, _, _ in found:
    if full == SLUG:
        continue
    subprocess.run(["git", "remote", "remove", owner], capture_output=True)
    subprocess.run(["git", "remote", "add", owner, url], check=True)
    added += 1

print(f"Added {added} classmate(s). Fetching...")
subprocess.run(["git", "fetch", "--all", "--quiet"])
print()
print("Done. Now try:")
print("  ./scripts/tree.sh")
print("  git branch -r")
PY
