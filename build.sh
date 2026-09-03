#!/usr/bin/env bash
# Full deterministic build. Everything here works offline from committed data,
# so CI and a laptop produce the same site.
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
python3 pipeline/loop_maps.py  > /dev/null
python3 pipeline/loop_signs.py > /dev/null

# Icons take ~10s to rasterise and never change. Rebuild only when missing,
# or when asked with:  ./build.sh --icons
if [ "${1:-}" = "--icons" ] || [ ! -f static/icon-512.png ]; then
  python3 pipeline/icons.py > /dev/null
fi

hugo --minify --cleanDestinationDir "${@:2}"
echo
echo "-> public/  ($(find public -name '*.html' | wc -l | tr -d ' ') pages)"
