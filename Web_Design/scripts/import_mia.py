"""Export a pinned Mia handoff to static, per-country frontend files."""
import json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
REF = "origin/Mia_womengap"
commit = subprocess.check_output(["git", "rev-parse", REF], cwd=REPO, text=True).strip()
def load(name):
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:handoff/ui/{name}.json"], cwd=REPO))
summary, trajectories, indicators = load("countries"), load("trajectories"), load("indicators")
destination = ROOT / "public/data/mia"
destination.mkdir(parents=True, exist_ok=True)
for row in summary:
    iso = row["iso"]
    payload = {"summary": row, "years": trajectories["years"], "trajectories": trajectories["countries"].get(iso, {}), "indicators": indicators.get(iso, [])}
    (destination / f"{iso}.json").write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
for name in ["global_summary", "early_warning"]:
    (destination / f"{name}.json").write_text(json.dumps(load(name), ensure_ascii=False, allow_nan=False), encoding="utf-8")
metadata = {"branch": REF, "commit": commit, "sourceUrl": f"https://github.com/ErHxyun/Carolina-Data-Challenge-2026/tree/{commit}/handoff", "headlineYear": 2021, "countries": len(summary)}
(destination / "provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
(destination / "DATA_DICTIONARY.md").write_bytes(subprocess.check_output(["git", "show", f"{commit}:handoff/DATA_DICTIONARY.md"], cwd=REPO))
codes = {r["iso"] for r in summary}
geometry = json.loads((ROOT / "src/data/countries.geo.json").read_text(encoding="utf-8"))
lookup = {}
for feature in geometry["features"]:
    p = feature["properties"]
    if p["ADMIN"] == "Antarctica": continue
    lookup[p["ADMIN"]] = next((p[k] for k in ["WB_A3", "ISO_A3", "ISO_A3_EH", "ADM0_A3"] if p.get(k) in codes), None)
(ROOT / "src/data/researchCountryCodes.json").write_text(json.dumps(lookup, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Exported {len(summary)} country files at {commit[:7]}; {sum(v is not None for v in lookup.values())}/{len(lookup)} map features matched.")

import runpy
runpy.run_path(str(ROOT / "scripts/build_map_atlas.py"), run_name="__main__")
