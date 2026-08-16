#!/usr/bin/env bash
# Runs once when a Codespace is created. Its whole job is to make the terminal feel welcoming rather than alarming.
set -euo pipefail

git config --global --add safe.directory "$PWD" 2>/dev/null || true

# A short, friendly prompt: the folder you are in and the branch you are on, and nothing else.
cat >> ~/.bashrc <<'EOF'

# OurStory: a small prompt that shows which branch you are on.
parse_branch() { git branch --show-current 2>/dev/null | sed 's/.*/ (&)/'; }
PS1='\[\033[1;34m\]\W\[\033[0;33m\]$(parse_branch)\[\033[0m\] $ '
alias tree='./scripts/tree.sh'
alias who-wrote-what='./scripts/blame.sh'
EOF

chmod +x scripts/*.sh 2>/dev/null || true
echo "Codespace ready. Type 'cat CHEATSHEET.md' if you want the list of commands again."
