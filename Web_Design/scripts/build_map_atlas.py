"""Build national map values from existing Mia exports, without subnational inference."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / "public/data/mia"
dimensions = ["Overall", "Education", "Employment", "Health", "Infrastructure"]
countries = {}
for path in sorted(folder.glob("???.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    countries[data["summary"]["iso"]] = {"summary": data["summary"], "gaps": {
        dimension: [round(u-r, 4) if isinstance(u, (float,int)) and isinstance(r, (float,int)) else None
                    for r,u in zip(series["rural_women"]["median"],series["urban_women"]["median"])]
        for dimension,series in data["trajectories"].items() if dimension in dimensions}}
    years = data["years"]
payload = {"years": years, "dimensions": dimensions, "countries": countries,
           "provenance": json.loads((folder / "provenance.json").read_text(encoding="utf-8"))}
(folder / "map_atlas.json").write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")),encoding="utf-8")
print(f"Exported national map atlas: {len(countries)} countries.")
