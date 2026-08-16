#!/usr/bin/env bash
#
# Show the commit tree in a terminal, for projecting during class.
#
#   ./scripts/tree.sh          once
#   ./scripts/tree.sh --watch  redraw every few seconds as pull requests land
#
# This is the same picture as the "The tree" page on the website, just in the terminal, which is handy inside a Codespace.

set -euo pipefail

draw() {
  git fetch --all --quiet 2>/dev/null || true
  git log --graph --all --decorate --oneline --date-order \
    --pretty=format:'%C(auto)%h%d %C(bold blue)%an%C(reset) %s'
}

if [ "${1:-}" = "--watch" ]; then
  while true; do
    clear
    printf '\033[1mOur story, as it stands\033[0m   (Ctrl-C to stop)\n\n'
    draw
    sleep "${WATCH_SECONDS:-10}"
  done
else
  draw
fi
