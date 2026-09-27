"""Export team time-use results for the static country dashboard."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Agent_Backend"))
from server import COUNTRIES, DATA, FILES, rows_for
root = Path(__file__).resolve().parents[1] / "public/data/time_tax"
root.mkdir(parents=True, exist_ok=True)
output = {}
for iso in sorted({v for v in COUNTRIES.values() if v}):
    records = {topic: {"source": "Graduate_Dataset/analysis_results/" + path, "rows": rows_for(DATA / path, iso)} for topic, path in FILES.items()}
    if any(item["rows"] for item in records.values()):
        output[iso] = records
(root / "countries.json").write_text(json.dumps(output, ensure_ascii=False, allow_nan=False), encoding="utf-8")
print("Exported time-use records for", len(output), "countries.")
