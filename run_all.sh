#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-.venv/bin/python}"
if [[ ! -x "$PY" ]]; then PY=python3; fi

"$PY" src/01_universe.py
"$PY" src/02_download_klines.py
"$PY" src/03_download_funding.py
"$PY" src/04_download_dvol.py
"$PY" src/05_download_expiries.py
"$PY" src/06_macro_calendar.py
"$PY" src/07_market_hours.py
"$PY" src/08_unlocks.py
"$PY" src/09_clean.py
"$PY" src/10_build_db.py
"$PY" src/11_qa_report.py
echo "Done. See docs/qa_report.md"
