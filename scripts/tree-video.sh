#!/usr/bin/env bash
#
# Make a short film of the story being written, for the end of the class.
#
#   ./scripts/tree-video.sh            writes ourstory.mp4
#   ./scripts/tree-video.sh finale     writes finale.mp4
#
# Gource replays the history with each contributor appearing by name as their work lands.
# It is a nice thirty seconds to end on, but be aware of what it actually shows: gource visualises the *file tree* changing over time, and this repository is essentially one file.
# So you get everybody's name converging on story.md rather than a spreading tree.
# For the branch-and-merge picture, use ./scripts/tree-image.sh or the website instead.
#
# This is deliberately local-only and never runs in CI.

set -euo pipefail

NAME="${1:-ourstory}"
SECONDS_TOTAL="${SECONDS_TOTAL:-30}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

missing=""
command -v gource >/dev/null 2>&1 || missing="gource"
command -v ffmpeg >/dev/null 2>&1 || missing="${missing:+$missing and }ffmpeg"

if [ -n "$missing" ]; then
  cat >&2 <<EOF
This needs $missing, which does not seem to be installed.

  macOS          brew install gource ffmpeg
  Debian/Ubuntu  sudo apt-get install gource ffmpeg

Nothing else in this repository depends on them; this script is an optional extra.
EOF
  exit 69
fi

TITLE="$(head -1 instance.txt 2>/dev/null || echo 'Our story')"

# --seconds-per-day is what actually controls the pace. The whole history happens on one or two days, so it is set from the total running time you asked for rather than from the calendar.
gource \
  --title "$TITLE" \
  --seconds-per-day "$SECONDS_TOTAL" \
  --auto-skip-seconds 0.5 \
  --file-idle-time 0 \
  --key \
  --highlight-users \
  --hide filenames,progress,mouse \
  --background-colour 16151A \
  --font-size 22 \
  --output-framerate 30 \
  --stop-at-end \
  -1280x720 \
  --output-ppm-stream - \
  | ffmpeg -y -loglevel error -r 30 -f image2pipe -vcodec ppm -i - \
      -vcodec libx264 -pix_fmt yuv420p -crf 22 "$NAME.mp4"

echo "Wrote $NAME.mp4"
