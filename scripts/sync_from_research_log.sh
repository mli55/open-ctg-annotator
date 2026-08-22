#!/bin/sh
# Refresh this repo from the live working copies in research_log.
set -e
SRC="/Users/ashl/Library/Mobile Documents/com~apple~CloudDocs/JC/ARPH/research_log/scripts/decel_annotator"
ANN="/Users/ashl/Library/Mobile Documents/com~apple~CloudDocs/JC/ARPH/research_log/annotations/decel_manual"
cd "$(dirname "$0")/.."
cp "$SRC"/annotator.html tool/annotator.html
cp "$SRC"/annotator.html public/index.html
cp "$SRC"/serve.py "$SRC"/claude_pass.py "$SRC"/make_pilot_list.py "$SRC"/README.md tool/
cp "$SRC"/pilot.json tool/pilot.json
cp "$SRC"/pilot.json public/pilot.json
# the CTU expert reference overlay travels with the page
mkdir -p public/expert public/baselines
rsync -a --delete "$ANN/shared/" annotations/shared/
rsync -a --delete "$ANN/claude/" annotations/claude/
echo "synced; review with git diff, then commit"
