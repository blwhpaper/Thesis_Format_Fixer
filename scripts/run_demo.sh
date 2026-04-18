#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Please run scripts/bootstrap.sh first"
  exit 1
fi

source .venv/bin/activate

python3 -m thesis_format_fixer.cli --help
python3 -m thesis_format_fixer.cli check samples/input/demo.docx || true
python3 -m thesis_format_fixer.cli fix samples/input/demo.docx --out samples/output/demo.fixed.docx || true
