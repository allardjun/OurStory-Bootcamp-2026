#!/usr/bin/env bash
#
# Draw the commit tree as a standalone image, for slides or printing.
#
#   ./scripts/tree-image.sh            writes tree.svg and tree.png
#   ./scripts/tree-image.sh talk       writes talk.svg and talk.png
#
# This is the same graph as the "The tree" page on the website, drawn from the same code, but with the colours baked in so the file stands on its own.
# The PNG is rendered at a high resolution so it survives being projected or zoomed into.

set -euo pipefail

NAME="${1:-tree}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v dot >/dev/null 2>&1; then
  cat >&2 <<'EOF'
This needs Graphviz, which does not seem to be installed.

  macOS          brew install graphviz
  Debian/Ubuntu  sudo apt-get install graphviz

The website version of this picture is built for you automatically and needs nothing installed.
EOF
  exit 69
fi

python3 site/build.py --dot > "$NAME.dot"

dot -Tsvg "$NAME.dot" -o "$NAME.svg"
dot -Tpng -Gdpi=192 "$NAME.dot" -o "$NAME.png"
rm -f "$NAME.dot"

echo "Wrote:"
ls -lh "$NAME.svg" "$NAME.png" | awk '{print "  " $NF "  " $5}'
