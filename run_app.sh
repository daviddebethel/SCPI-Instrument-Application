#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")"
python3 -m dmm_app.main
