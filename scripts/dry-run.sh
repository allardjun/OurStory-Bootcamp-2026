#!/usr/bin/env bash
#
# Rehearse a whole session in a throwaway copy of the repo.
#
#   ./scripts/dry-run.sh [number-of-students] [top|uniform]
#
# It invents a class, has each of them edit a line, merges everything, and reports how many hit a merge conflict.
# Nothing is pushed anywhere and your real repository is not touched.
#
# The second argument chooses how the imaginary students pick their lines:
#
#   top      (default) most of them edit near the beginning of the story
#   uniform            they pick with genuinely equal probability anywhere
#
# "top" is the realistic one. In the 2024 class, five of seven students edited within the first twelve lines of a hundred-and-twenty-line file, and four of them landed on the very same line.
# People do not pick uniformly, which is why a long story still produces plenty of conflicts.
# Run it with "uniform" to see how much of the conflict rate is due to that bias rather than to the length of the story.

set -euo pipefail

STUDENTS="${1:-12}"
BIAS="${2:-top}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"

git clone -q "$SRC" "$WORK/repo"
cd "$WORK/repo"

# Decide who edits which line, using the chosen model of how people choose.
CHOICES=()
while IFS= read -r n; do CHOICES+=("$n"); done < <(python3 - "$STUDENTS" "$BIAS" <<'PY'
import pathlib, random, re, sys

students, bias = int(sys.argv[1]), sys.argv[2]

# Every line a student could plausibly land on: real text, not the title or the byline.
editable, seen_title, seen_byline = [], False, False
for n, text in enumerate(pathlib.Path("story.md").read_text().split("\n"), start=1):
    s = text.strip()
    if not s:
        continue
    if s.startswith("<!--") and s.endswith("-->"):
        continue
    if not seen_title and s.startswith("# "):
        seen_title = True
        continue
    if not seen_byline and re.fullmatch(r"[_*].+[_*]", s):
        seen_byline = True
        continue
    editable.append(n)

if bias == "uniform":
    picks = [random.choice(editable) for _ in range(students)]
else:
    # Seven in ten students edit somewhere in the first dozen lines; the rest go anywhere.
    # This is a rough fit to the one class we have data for, not a law of nature.
    head = editable[:12] or editable
    picks = [random.choice(head if random.random() < 0.7 else editable)
             for _ in range(students)]

print(len(editable))
for p in picks:
    print(p)
PY
)

EDITABLE="${CHOICES[0]}"
CHOICES=("${CHOICES[@]:1}")

echo "Story has $EDITABLE editable lines; $STUDENTS students picking with '$BIAS' bias."
echo

# Everyone forks at the same moment, before any merging starts.
# That is what makes conflicts possible: a student who forks after their classmates' work has already landed cannot collide with it.
BASE="$(git rev-parse main)"
NAMES=(ana ben cleo dev eli fern gus hana ivo jo kai lena mo nia omar pia quinn rae sam tess)

conflicts=0
for i in $(seq 1 "$STUDENTS"); do
  who="${NAMES[$(( (i - 1) % ${#NAMES[@]} ))]}$i"
  line="${CHOICES[$(( i - 1 ))]}"

  git checkout -q -b "$who" "$BASE"
  python3 - "$line" "$who" <<'PY'
import sys, pathlib
p = pathlib.Path("story.md")
lines = p.read_text().split("\n")
i = int(sys.argv[1]) - 1
lines[i] = lines[i].rstrip(".") + f", said {sys.argv[2]}."
p.write_text("\n".join(lines))
PY
  git commit -qam "$who edits line $line" --author="$who <$who@example.edu>"
  git checkout -q main

  if git -c user.name=Instructor -c user.email=i@example.edu \
       merge --no-ff -q "$who" -m "Merge pull request #$i from $who" >/dev/null 2>&1; then
    printf '  %-8s line %-4s merged cleanly\n' "$who" "$line"
  else
    conflicts=$(( conflicts + 1 ))
    printf '  %-8s line %-4s \033[33mCONFLICT\033[0m\n' "$who" "$line"
    # Resolve it the way a student would: keep both people's words, drop the markers.
    python3 - <<'PY'
import pathlib, re
p = pathlib.Path("story.md")
p.write_text("\n".join(l for l in p.read_text().split("\n")
                       if not re.match(r"^(<{7}|={7}|>{7})", l)))
PY
    git add story.md
    git -c user.name=Instructor -c user.email=i@example.edu \
        commit -qm "Merge pull request #$i from $who (conflict resolved)"
  fi
done

echo
echo "$conflicts of $STUDENTS students hit a merge conflict."
if [ "$conflicts" -lt $(( STUDENTS / 3 )) ]; then
  echo "That is low. Consider telling the class to edit near the start, or set HOT_LINES."
fi

python3 site/check_story.py || true
python3 site/build.py
echo
echo "Open $WORK/repo/_site/index.html to see how it will look."
