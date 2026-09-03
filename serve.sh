#!/usr/bin/env bash
# Local preview at the root, rather than under the /fort.mouse/ subpath that
# GitHub Pages serves from. Regenerates the data first, then watches.
set -euo pipefail
cd "$(dirname "$0")"
python3 pipeline/build_data.py > /dev/null
exec hugo server --baseURL "http://localhost:1313/" --port 1313 "$@"
