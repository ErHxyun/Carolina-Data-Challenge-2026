"""Indicator-level coverage audit of the raw World Bank source archive (Graduate_Dataset/all_sources).

    python3 scripts/audit_source_coverage.py --sources ../../inputs/graduate_all_sources \
        --package ../../github_package/womens-opportunity-conversion-map --out ../data_audit

Offline only; nothing here is shipped to the browser. Country coverage counts economies only: the
reference set is every ISO3 used by the project's existing analyses (public/data/mia country files
and the conversion package), so World Bank regional / income aggregates are excluded and counted
separately.
"""
import argparse, csv, gzip, json, re, statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMELINE = (1990, 2024)
FE = re.compile(r"\.(FE)(\.|$)|\bfemale\b|\bwomen\b", re.I)
MA = re.compile(r"\.(MA)(\.|$)|(?<!fe)\bmale\b|\bmen\b", re.I)
RURAL_URBAN = re.compile(r"\.(RU|UR)(\.|$)|\brural\b|\burban\b", re.I)


def economies(country_csv):
    iso = {p.stem for p in (ROOT / "public/data/mia").glob("???.json")}
    with open(country_csv, newline="", encoding="utf-8") as fh:
        iso |= {r["iso3"] for r in csv.DictReader(fh)}
    return iso


def row_iso(row):
    """WDI/GDS/ID4 put ISO3 in `iso3`; Findex, SE4ALL and JOIN leave it empty and use `country_id`."""
    iso = (row.get("iso3") or "").strip()
    if not iso:
        cid = (row.get("country_id") or "").strip()
        iso = cid if len(cid) == 3 and cid.isalpha() else ""
    return iso.upper()


def counterpart(code):
    """FE <-> MA sibling code, e.g. SL.TLF.CACT.FE.ZS <-> SL.TLF.CACT.MA.ZS."""
    if re.search(r"\.FE(\.|$)", code):
        return re.sub(r"\.FE(\.|$)", r".MA\1", code)
    if re.search(r"\.MA(\.|$)", code):
        return re.sub(r"\.MA(\.|$)", r".FE\1", code)
    return None


def cadence(years_by_country, all_years):
    spans = []
    for ys in years_by_country.values():
        ys = sorted(ys)
        spans.append(len(ys) / (ys[-1] - ys[0] + 1))
    density = statistics.median(spans) if spans else 0
    if len(all_years) <= 2:
        return "snapshot", density
    gaps = [b - a for a, b in zip(sorted(all_years), sorted(all_years)[1:])]
    if len(all_years) <= 10 and statistics.median(gaps) >= 2:
        return "survey_wave", density
    if density >= 0.8 and len(all_years) >= 15:
        return "annual", density
    return "intermittent", density


def audit_file(path, keep):
    by_country, years, obs, aggregates = defaultdict(set), set(), 0, set()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            iso, value = row_iso(row), (row.get("value") or "").strip()
            if iso not in keep:
                aggregates.add(iso or row.get("country_id", ""))
                continue
            if value == "":
                continue
            try:
                year = int(str(row["date"])[:4])
                float(value)
            except ValueError:
                continue
            by_country[iso].add(year)
            years.add(year)
            obs += 1
    return by_country, years, obs, aggregates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--package", required=True, type=Path, help="womens-opportunity-conversion-map folder")
    a = ap.parse_args()
    keep = economies(a.package / "data/map/country_map_layers.csv")
    rows, summary = [], []
    for source_dir in sorted(p for p in a.sources.iterdir() if p.is_dir()):
        source_id = source_dir.name
        names = {}
        meta = source_dir / "_indicators.csv"
        if meta.exists():
            with open(meta, newline="", encoding="utf-8") as fh:
                names = {r["id"]: r["name"] for r in csv.DictReader(fh)}
        log = {}
        if (source_dir / "_log.csv").exists():
            with open(source_dir / "_log.csv", newline="", encoding="utf-8") as fh:
                log = {r["indicator"]: r for r in csv.DictReader(fh)}
        files = sorted(source_dir.glob("*.csv.gz"))
        codes = {f.name[:-7] for f in files}
        src_rows = []
        for f in files:
            code = f.name[:-7]
            by_country, years, obs, _ = audit_file(f, keep)
            name = names.get(code, "")
            kind, density = cadence(by_country, years) if years else ("no_data", 0)
            in_window = [len([y for y in ys if TIMELINE[0] <= y <= TIMELINE[1]]) for ys in by_country.values()]
            median_window_years = statistics.median(in_window) if in_window else 0
            timeline_ok = (kind == "annual" and years and min(years) <= 2000 and max(years) >= 2019
                           and len(by_country) >= 100 and median_window_years >= 15)
            sibling = counterpart(code)
            text = f"{code} {name}"
            src_rows.append({
                "source_id": source_id, "indicator_code": code, "indicator_name": name,
                "earliest_year": min(years) if years else "", "latest_year": max(years) if years else "",
                "distinct_years": len(years), "countries": len(by_country), "non_null_observations": obs,
                "median_country_years_1990_2024": median_window_years,
                "median_within_country_density": round(density, 2),
                "is_female_or_male_series": bool(FE.search(text) or MA.search(text)),
                "female_and_male_versions_exist": bool(sibling and sibling in codes),
                "rural_or_urban_series": bool(RURAL_URBAN.search(text)),
                "cadence": kind,
                "supports_1990_2024_timeline": bool(timeline_ok),
                "snapshot_only": kind in ("snapshot", "survey_wave") or (kind == "intermittent" and not timeline_ok),
            })
        missing = [c for c, r in log.items() if r.get("status") != "ok" or r.get("rows") in ("0", "")]
        rows += src_rows
        summary.append({
            "source_id": source_id, "indicator_files": len(files), "indicators_listed": len(names),
            "failed_or_empty_downloads": len(missing),
            "indicators_with_data": sum(1 for r in src_rows if r["non_null_observations"]),
            "earliest_year": min((r["earliest_year"] for r in src_rows if r["earliest_year"] != ""), default=""),
            "latest_year": max((r["latest_year"] for r in src_rows if r["latest_year"] != ""), default=""),
            "timeline_eligible": sum(r["supports_1990_2024_timeline"] for r in src_rows),
            "cadence_counts": json.dumps(dict(sorted(
                {k: sum(r["cadence"] == k for r in src_rows) for k in {r["cadence"] for r in src_rows}}.items()))),
        })
        print(f"{source_id}: {len(files)} files audited")
    a.out.mkdir(parents=True, exist_ok=True)

    def write(name, data):
        with open(a.out / name, "w", newline="", encoding="utf-8") as fh:
            if not data:
                fh.write("")
                return
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    write("indicator_coverage.csv", rows)
    write("source_summary.csv", summary)
    write("timeline_eligible_indicators.csv", [r for r in rows if r["supports_1990_2024_timeline"]])
    write("snapshot_only_indicators.csv", [r for r in rows if r["snapshot_only"]])
    (a.out / "audit_meta.json").write_text(json.dumps({
        "economies_reference_set": len(keep), "timeline_window": TIMELINE,
        "rules": {
            "annual": ">=15 distinct years and median within-country density >=0.8",
            "survey_wave": "<=10 distinct years with median gap >=2 years",
            "snapshot": "<=2 distinct years",
            "supports_1990_2024_timeline": "annual, starts <=2000, ends >=2019, >=100 economies, median >=15 observed years per economy in 1990-2024",
        }}, indent=2))
    print(f"{len(rows)} indicators audited; {sum(r['supports_1990_2024_timeline'] for r in rows)} timeline-eligible")


if __name__ == "__main__":
    main()
