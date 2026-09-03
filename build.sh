#!/usr/bin/env bash
# Full build: validate, resolve, render.
set -euo pipefail
cd "$(dirname "$0")"
python3 pipeline/build_data.py
hugo --logLevel warn --cleanDestinationDir
echo "-> public/  (rsync -a --delete public/ user@server:/var/www/fortmouse/)"
