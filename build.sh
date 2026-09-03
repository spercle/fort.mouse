#!/usr/bin/env bash
# Full build: validate, resolve, render.
set -euo pipefail
cd "$(dirname "$0")"

# `hugo --cleanDestinationDir` deletes public/ out from under a running
# `hugo server`, which leaves it serving 404s. Refuse rather than break it.
if pgrep -f "hugo server" > /dev/null 2>&1; then
  echo "hugo server is running — stop it first (pkill -f 'hugo server')." >&2
  echo "A dev server rebuilds on its own; you do not need build.sh while it runs." >&2
  exit 1
fi
python3 pipeline/build_data.py
hugo --logLevel warn --cleanDestinationDir
echo "-> public/  (rsync -a --delete public/ user@server:/var/www/fortmouse/)"
