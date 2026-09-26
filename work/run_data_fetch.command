#!/bin/bash
# Double-click to download World Bank sources 2 (WDI), 28 (Findex), 29 (ASPIRE), 89 (ID4D)
cd "$(dirname "$0")"
OUT="$(cd .. && pwd)/outputs/world_bank_sources"
PY=python3
$PY -c "import requests, pandas" 2>/dev/null || $PY -m pip install --user requests pandas
$PY data_fetch.py --sources 2 28 29 89 --out "$OUT"
echo; echo "Download finished. You can close this window (Claude will merge the tables)."
