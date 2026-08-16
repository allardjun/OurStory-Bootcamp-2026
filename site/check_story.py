#!/usr/bin/env python3
"""Check story.md before it is merged.

This is the "continuous integration" half of the activity: a small program that runs automatically on every pull request and either passes or fails.
It deliberately checks the two things that actually go wrong when a beginner resolves a merge conflict in the GitHub web editor, and it explains them in plain English rather than in git's vocabulary.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

CONFLICT = re.compile(r"^(<{7}|={7}|>{7})(\s|$)")


def fail(title, *body):
    print(f"\n✗ {title}\n")
    for para in body:
        print(f"  {para}\n")
    return 1


def ok(msg):
    print(f"✓ {msg}")
    return 0


def base_line_count(base, path):
    """How many non-blank lines the story had before this pull request touched it."""
    try:
        out = subprocess.run(["git", "show", f"{base}:{path}"],
                             capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None
    return sum(1 for line in out.split("\n") if line.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", default="story.md")
    ap.add_argument("--base", default="", help="ref to compare against, e.g. origin/main")
    args = ap.parse_args()

    path = Path(args.story)
    if not path.exists():
        return fail(
            f"{args.story} is missing.",
            "The story file was deleted or renamed. Every change in this repository should leave a "
            f"file called {args.story} in place.",
        )

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    live = [line for line in lines if line.strip()]

    if not live:
        return fail(f"{args.story} is empty.",
                    "Something removed all the text. Try your edit again from a fresh copy.")

    markers = [(i, line) for i, line in enumerate(lines, start=1) if CONFLICT.match(line)]
    if markers:
        where = "\n  ".join(f"line {i}: {line.strip()[:60]}" for i, line in markers[:6])
        return fail(
            "The story still has merge-conflict markers in it.",
            f"Found {len(markers)} of them:\n\n  {where}",
            "This is normal and easy to fix. When two people change the same line, git writes both "
            "versions into the file and marks them with <<<<<<<, ======= and >>>>>>>.",
            "Your job is to decide which words you want to keep, and then delete the other version "
            "AND all three marker lines. Nothing that starts with <<<<<<<, ======= or >>>>>>> should "
            "survive. Edit the file again and commit.",
        )

    if not any(line.strip().startswith("# ") for line in lines):
        return fail(
            "The story has lost its title.",
            f"The first line of {args.story} should start with '# '. It was probably deleted by "
            "accident while resolving a conflict.",
        )

    if args.base:
        before = base_line_count(args.base, args.story)
        if before and len(live) < before * 0.6:
            return fail(
                "This change deletes most of the story.",
                f"The story had {before} lines and now has {len(live)}.",
                "That usually means a merge conflict was resolved by keeping only one side of the "
                "file. Open the story, put the missing lines back, and commit again. If you really "
                "did mean to cut it down, tell the instructor and they can merge it anyway.",
            )

    return ok(f"{args.story} looks good: {len(live)} lines, no leftover conflict markers.")


if __name__ == "__main__":
    sys.exit(main())
