"""Build compact, browser-ready JSON for the education-to-employment conversion view.

    python3 scripts/build_conversion_web_data.py \
        --package ../../github_package/womens-opportunity-conversion-map \
        --sources ../../inputs/graduate_all_sources

Inputs (offline only; never fetched by the browser):
  * the conversion map package (model outputs, layer catalog, reviewed evidence reports);
  * a small, audited subset of the raw World Bank archive (Graduate_Dataset/all_sources @ f234e5f).

Outputs in public/data/conversion/:
  snapshot_atlas.json   latest values per ISO3 (package outputs + observation years + country profiles)
  timeline_atlas.json   {layer: {years: [...], values: {ISO3: [v|null, ...]}}} aligned to `years`
  layers.json           layer registry (metadata, scale, temporal type, value type, coverage)
  coverage.json         per-layer country counts by year; per-country data-visibility metrics
  evidence_reports.json the six reviewed pilot reports keyed by ISO3, plus independent source-check notes
  provenance.json       inputs, counts, validation results, known discrepancies
Rules: ISO3 economies only (World Bank aggregates removed); actual observation years kept; nulls stay
null; no interpolation, forward/back fill or averaging. Nothing is written unless validation passes.
"""
import argparse, csv, gzip, hashlib, json, math, shutil, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "public/data/conversion"
WINDOW = (1990, 2024)
RAW_COMMIT = "f234e5f8e2b29c9f00313d733f29367871c4c7fa"

# ---------------------------------------------------------------------------- package layers
PRIMARY = {
    "education_employment_conversion_gap_z": "Education ahead of employment",
    "conversion_residual": "Opportunity conversion surprise",
    "conversion_shortfall": "Education progress without employment progress",
    "gap_momentum_state": "Gap momentum",
    "prob_gap_not_halved_within_15y": "Sticky-gap risk",
    "core_domains_observed": "Data visibility",
}
MORE = ["finance_gender_gap_pp", "digital_gender_gap_pp", "identity_female_pct", "time_tax_extra_hours_day",
        "maternal_mortality_ratio", "rural_time_tax_gap_latest_pp", "prob_gap_widening",
        "prob_employment_gap_halves_within_10y", "core_year_spread"]
DIVERGING = {"education_employment_conversion_gap_z", "conversion_residual", "conversion_shortfall",
             "finance_gender_gap_pp", "digital_gender_gap_pp"}
LOG = {"maternal_mortality_ratio"}
MODEL_OUTPUTS = {"education_employment_conversion_gap_z", "conversion_residual", "conversion_shortfall",
                 "gap_momentum_state", "prob_gap_widening", "prob_gap_not_halved_within_15y",
                 "prob_employment_gap_halves_within_10y", "desynchronization_sd", "development_delay_employment_years"}
PERIOD = {
    "education_employment_conversion_gap_z": "Latest available education and employment composites",
    "conversion_residual": "Latest available observations through 2024",
    "conversion_shortfall": "Endpoint change, 2000–2024 where available",
    "gap_momentum_state": "Latest modelled state (HMM panel 2003–2024)",
    "prob_gap_widening": "Latest modelled state (HMM panel 2003–2024)",
    "prob_gap_not_halved_within_15y": "Simulated from the fitted historical process",
    "prob_employment_gap_halves_within_10y": "Simulated from the fitted historical process",
    "core_domains_observed": "Coverage audit of education, employment, finance and digital domains",
    "core_year_spread": "Years between the oldest and newest core observation",
    "finance_gender_gap_pp": "Global Findex survey waves",
    "digital_gender_gap_pp": "Latest available year (not recorded in the package)",
    "identity_female_pct": "Global Findex / ID4D survey waves",
    "time_tax_extra_hours_day": "Latest available time-use survey",
    "rural_time_tax_gap_latest_pp": "Latest available rural–urban estimate",
    "maternal_mortality_ratio": "Latest available modelled estimate (WHO)",
    "desynchronization_sd": "Latest available core-domain composites",
    "development_delay_employment_years": "Trajectory matching analysis",
    "evidence_report_available": "Reviewed pilot, 2026",
}
SHORT_CAVEAT = {
    "education_employment_conversion_gap_z": "Indicators may cover different years and cohorts",
    "conversion_residual": "Model residual; not a causal effect",
    "conversion_shortfall": "Endpoint comparison; not the same cohort of women",
    "desynchronization_sd": "Compare with domain coverage",
    "gap_momentum_state": "Model state; not a forecast guarantee",
    "prob_gap_widening": "Model probability; not a forecast guarantee",
    "prob_employment_gap_halves_within_10y": "Conditional model probability, not a promise",
    "prob_gap_not_halved_within_15y": "Conditional model probability, not a promise",
    "development_delay_employment_years": "Trajectory analogy, not literal years behind",
    "core_domains_observed": "Coverage is not data quality",
    "core_year_spread": "Large spreads limit comparability across domains",
    "finance_gender_gap_pp": "Account ownership is not control over money",
    "digital_gender_gap_pp": "Definitions and years vary by country",
    "identity_female_pct": "Sparse coverage; ownership is not usable ID",
    "time_tax_extra_hours_day": "Sparse, not fully harmonized time-use surveys",
    "rural_time_tax_gap_latest_pp": "Household infrastructure context, not a women-only outcome",
    "maternal_mortality_ratio": "Modelled estimate; legend uses a log scale",
    "evidence_report_available": "Contextual evidence, not causal attribution",
}
UNIT_SHORT = {
    "standard deviations": "SD", "out-of-fold residual SD": "SD relative to model expectation",
    "difference in improvement SD": "SD difference in improvement",
    "within-country SD across observed core domains": "SD across domains", "state": "", "probability": "",
    "matched trajectory years": "matched trajectory years", "domains out of 4": "of 4 core domains observed",
    "years": "years between domain observations", "female minus male percentage points": "pp (women − men)",
    "percent of women": "% of women", "female minus male hours per day": "extra hours per day (women − men)",
    "composite gap points": "rural − urban gap points", "deaths per 100,000 live births": "deaths per 100,000 live births",
    "review available": "",
}
STRING_FIELDS = {"country", "region", "income_group", "trajectory_state", "archetype", "gap_momentum_state",
                 "rural_time_tax_gap_trend", "evidence_confidence", "evidence_mechanism_1"}
INT_FIELDS = {"core_domains_observed", "missing_core_domains", "latest_core_observation_year", "evidence_mechanism_count",
              "complicating_evidence_count"}
PROBABILITY_FIELDS = {"prob_gap_closing", "prob_gap_flat", "prob_gap_widening", "prob_employment_gap_halves_by_2030",
                      "prob_employment_gap_halves_within_10y", "prob_gap_not_halved_within_15y",
                      "prob_rural_time_tax_gap_shrinking", "residual_percentile"}
STATES = {"Closing": "prob_gap_closing", "Flat": "prob_gap_flat", "Widening": "prob_gap_widening"}

# ---------------------------------------------------------------------------- raw-source layers
# Selected after the coverage audit (integration_work/data_audit). Every entry records why.
RAW = {  # key: (source dir, indicator code)
    "edu_gpi_secondary": ("002_WDI", "SE.ENR.SECO.FM.ZS"),
    "edu_gpi_tertiary": ("002_WDI", "SE.ENR.TERT.FM.ZS"),
    "edu_sec_fe": ("002_WDI", "SE.SEC.ENRR.FE"), "edu_sec_ma": ("002_WDI", "SE.SEC.ENRR.MA"),
    "edu_ter_fe": ("002_WDI", "SE.TER.ENRR.FE"), "edu_ter_ma": ("002_WDI", "SE.TER.ENRR.MA"),
    "edu_prm_cmpt_fe": ("002_WDI", "SE.PRM.CMPT.FE.ZS"), "edu_lsec_cmpt_fe": ("002_WDI", "SE.SEC.CMPT.LO.FE.ZS"),
    "lfpr_ratio": ("002_WDI", "SL.TLF.CACT.FM.ZS"),
    "lfpr_fe": ("002_WDI", "SL.TLF.CACT.FE.ZS"), "lfpr_ma": ("002_WDI", "SL.TLF.CACT.MA.ZS"),
    "vuln_fe": ("002_WDI", "SL.EMP.VULN.FE.ZS"), "vuln_ma": ("002_WDI", "SL.EMP.VULN.MA.ZS"),
    "wage_fe": ("002_WDI", "SL.EMP.WORK.FE.ZS"), "wage_ma": ("002_WDI", "SL.EMP.WORK.MA.ZS"),
    "family_fe": ("002_WDI", "SL.FAM.WORK.FE.ZS"), "family_ma": ("002_WDI", "SL.FAM.WORK.MA.ZS"),
    "self_fe": ("002_WDI", "SL.EMP.SELF.FE.ZS"), "self_ma": ("002_WDI", "SL.EMP.SELF.MA.ZS"),
    "unemp_fe": ("002_WDI", "SL.UEM.TOTL.FE.ZS"), "unemp_ma": ("002_WDI", "SL.UEM.TOTL.MA.ZS"),
    "mgmt_fe": ("002_WDI", "SL.EMP.SMGT.FE.ZS"),
    "elec_ru": ("002_WDI", "EG.ELC.ACCS.RU.ZS"), "elec_ur": ("002_WDI", "EG.ELC.ACCS.UR.ZS"),
    "cook_ru": ("002_WDI", "EG.CFT.ACCS.RU.ZS"), "cook_ur": ("002_WDI", "EG.CFT.ACCS.UR.ZS"),
    "time_fe": ("014_GDS", "SG.TIM.UWRK.FE"), "time_ma": ("014_GDS", "SG.TIM.UWRK.MA"),
    "acct_fe": ("028_FDX", "account.t.d.1"), "acct_ma": ("028_FDX", "account.t.d.2"),
    "id_fe": ("089_ID4", "ID.OWN.TOTL.FE.ZS"),
}
SELECTION_REASONS = {
    "SE.ENR.SECO.FM.ZS": "Official UNESCO gender parity index for secondary enrollment; observed (not modelled), ~21 observed years per economy in 1990-2024, 204 economies. Education side of the historical conversion gap.",
    "SE.ENR.TERT.FM.ZS": "Tertiary enrollment parity; observed, 202 economies. Used in the data-visibility metric.",
    "SE.SEC.ENRR.FE": "Female/male secondary gross enrollment for the country profile (observed).",
    "SE.TER.ENRR.FE": "Female/male tertiary gross enrollment for the country profile (observed).",
    "SE.PRM.CMPT.FE.ZS": "Observed completion series used only in the data-visibility metric.",
    "SE.SEC.CMPT.LO.FE.ZS": "Observed completion series used only in the data-visibility metric.",
    "SL.TLF.CACT.FM.ZS": "Female-to-male labour-force participation ratio; annual 1990-2024, 186 economies. ILO modelled estimate; employment side of the historical conversion gap.",
    "SL.TLF.CACT.FE.ZS": "Women's labour-force participation over time (ILO modelled estimate), 186 economies.",
    "SL.EMP.VULN.FE.ZS": "Vulnerable employment separates access from quality (ILO modelled estimate), 1991-2024.",
    "SL.EMP.WORK.FE.ZS": "Wage and salaried share: employment-quality profile (ILO modelled).",
    "SL.FAM.WORK.FE.ZS": "Contributing family workers: unpaid family work (ILO modelled).",
    "SL.EMP.SELF.FE.ZS": "Self-employment share (ILO modelled).",
    "SL.UEM.TOTL.FE.ZS": "Unemployment rate (ILO modelled).",
    "SL.EMP.SMGT.FE.ZS": "Women in senior and middle management: advancement; observed but sparse (median 7 years), latest snapshot only.",
    "EG.ELC.ACCS.RU.ZS": "Rural vs urban electricity access, annual 1990-2024, 213 economies: rural infrastructure context for time poverty.",
    "EG.CFT.ACCS.RU.ZS": "Rural vs urban clean-cooking access, annual 2000-2023, 189 economies (WHO estimates).",
    "SG.TIM.UWRK.FE": "Direct unpaid-work time use; only 27 economies and 66 observations, so snapshot only (with survey year).",
    "account.t.d.1": "Findex account ownership female/male: genuine survey waves 2011-2024; shown as waves, never annual.",
    "ID.OWN.TOTL.FE.ZS": "ID ownership among women: Findex/ID4D survey waves 2017-2024; shown as waves, never annual.",
}

HISTORICAL = [  # timeline layers, in display order
    dict(id="education_gap_timeline", label="Education gender gap over time",
         question="How far is girls' secondary enrollment from parity with boys'?",
         unit="parity index minus 1", unit_short="vs parity (secondary enrollment)", type="continuous_signed",
         palette="orange_to_blue_diverging", scale="diverging", value_type="observed",
         direction="Negative means girls enrol less than boys; positive means girls enrol more",
         source="UNESCO via World Bank WDI (SE.ENR.SECO.FM.ZS)",
         caveat="Gross enrollment parity, not completion or learning; observed years only, gaps are shown as missing.",
         short_caveat="Observed years only; enrollment is not completion"),
    dict(id="employment_gap_timeline", label="Employment gender gap over time",
         question="How far is women's labour-force participation from men's?",
         unit="participation ratio minus 1", unit_short="vs parity (labour-force participation)",
         type="continuous_signed", palette="orange_to_blue_diverging", scale="diverging", value_type="modelled",
         direction="Negative means women participate less than men",
         source="ILO modelled estimates via World Bank WDI (SL.TLF.CACT.FM.ZS)",
         caveat="ILO modelled estimates, not direct observations; participation includes informal and vulnerable work.",
         short_caveat="ILO modelled estimate; includes informal work"),
    dict(id="conversion_gap_timeline", label="Education–employment conversion gap over time",
         question="In which years was education closer to gender parity than employment?",
         unit="parity points", unit_short="parity points (education − employment)", type="continuous_signed",
         palette="gold_to_pink_diverging", scale="diverging", value_type="mixed",
         direction="Higher means education is closer to parity than labour-force participation",
         source="Derived: (SE.ENR.SECO.FM.ZS − 1) − (SL.TLF.CACT.FM.ZS/100 − 1), same year only",
         caveat="Shown only where an observed education value and a modelled employment value exist for the same year. Different age groups and cohorts; not a transition rate.",
         short_caveat="Observed education vs modelled employment; different cohorts"),
    dict(id="female_lfpr_timeline", label="Women's labour-force participation over time",
         question="What share of women aged 15+ are in the labour force?", unit="percent of women 15+",
         unit_short="% of women 15+", type="percentage", palette="light_to_blue_sequential", scale="sequential",
         value_type="modelled", direction="Higher means more women in the labour force",
         source="ILO modelled estimates via World Bank WDI (SL.TLF.CACT.FE.ZS)",
         caveat="Participation is not job quality: it includes vulnerable, informal and unpaid family work.",
         short_caveat="ILO modelled estimate; participation is not job quality"),
    dict(id="female_vulnerable_employment_timeline", label="Women's vulnerable employment over time",
         question="What share of employed women are own-account or contributing family workers?",
         unit="percent of female employment", unit_short="% of employed women", type="percentage",
         palette="light_to_orange_sequential", scale="sequential", value_type="modelled",
         direction="Higher means more of women's work is vulnerable",
         source="ILO modelled estimates via World Bank WDI (SL.EMP.VULN.FE.ZS)",
         caveat="ILO modelled estimates; a proxy for insecure work, not a direct measure of earnings or conditions.",
         short_caveat="ILO modelled estimate"),
    dict(id="rural_electricity_gap_timeline", label="Rural electricity gap over time",
         question="How far does rural electricity access lag urban access?", unit="percentage points",
         unit_short="pp (urban − rural access)", type="continuous", palette="light_to_gold_sequential",
         scale="sequential", value_type="compiled",
         direction="Higher means rural households lag further behind urban households",
         source="SDG 7.1.1 Electrification Dataset via World Bank WDI (EG.ELC.ACCS.UR/RU.ZS)",
         caveat="Household access applies to women and men alike; compiled from surveys and estimates. Context for time poverty, not a women-only outcome.",
         short_caveat="Household context, not a women-only outcome"),
    dict(id="rural_clean_cooking_gap_timeline", label="Rural clean-cooking gap over time",
         question="How far does rural access to clean cooking lag urban access?", unit="percentage points",
         unit_short="pp (urban − rural access)", type="continuous", palette="light_to_gold_sequential",
         scale="sequential", value_type="modelled",
         direction="Higher means rural households lag further behind urban households",
         source="WHO estimates via World Bank WDI (EG.CFT.ACCS.UR/RU.ZS)",
         caveat="Modelled household estimates; relevant to fuel-collection time but not a direct time-use measure.",
         short_caveat="Modelled household estimate"),
]
VISIBILITY = [
    dict(id="observed_education_years", label="Data invisibility: observed education years",
         question="In how many years since 1990 was girls' and boys' secondary enrollment actually observed?",
         unit="observed years, 1990–2024", unit_short="observed years since 1990", type="integer",
         palette="light_to_blue_sequential", scale="sequential", value_type="coverage",
         direction="Lower means the education record is thinner", source="Coverage of SE.ENR.SECO.FM.ZS",
         caveat="Counts observations, not data quality. Modelled series (e.g. ILO) are excluded.",
         short_caveat="Counts observed years only"),
    dict(id="observed_missing_share", label="Data invisibility: missing observed country-years",
         question="What share of possible country-years are missing in observed gender-disaggregated series?",
         unit="share of country-years missing", unit_short="of possible country-years missing", type="share",
         palette="light_to_orange_sequential", scale="sequential", value_type="coverage",
         direction="Higher means more of the record is missing",
         source="Coverage of 4 observed education series (1990–2024) and women in management (2000–2024)",
         caveat="Measures what is missing from observed statistics; modelled series are excluded because they are always complete.",
         short_caveat="Observed gender-disaggregated series only"),
]
VISIBILITY_SERIES = [("edu_gpi_secondary", 1990), ("edu_gpi_tertiary", 1990), ("edu_prm_cmpt_fe", 1990),
                     ("edu_lsec_cmpt_fe", 1990), ("mgmt_fe", 2000)]
PROFILE = [  # employment-quality profile shown on the country page; all separate, no composite score
    ("Labour-force participation", "lfpr_fe", "lfpr_ma", "% of population 15+", "modelled"),
    ("Wage and salaried workers", "wage_fe", "wage_ma", "% of employment", "modelled"),
    ("Vulnerable employment", "vuln_fe", "vuln_ma", "% of employment", "modelled"),
    ("Contributing family workers", "family_fe", "family_ma", "% of employment", "modelled"),
    ("Self-employed", "self_fe", "self_ma", "% of employment", "modelled"),
    ("Unemployment", "unemp_fe", "unemp_ma", "% of labour force", "modelled"),
    ("Women in senior and middle management", "mgmt_fe", None, "% of managers", "observed"),
    ("Secondary gross enrollment", "edu_sec_fe", "edu_sec_ma", "% gross", "observed"),
    ("Tertiary gross enrollment", "edu_ter_fe", "edu_ter_ma", "% gross", "observed"),
]


# ---------------------------------------------------------------------------- helpers
def quantile(values, q):
    ordered = sorted(values)
    if not ordered:
        return None
    pos = (len(ordered) - 1) * q
    low, high = math.floor(pos), min(math.floor(pos) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def nice(value):
    if not value:
        return 1
    step = 10 ** (math.floor(math.log10(abs(value))) - 1)
    return round(math.ceil(value / step) * step, 10)


def r4(v):
    return round(v, 4) if isinstance(v, float) else v


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_cell(field, raw, errors, iso):
    value = raw.strip()
    if value == "":
        return None
    if field in STRING_FIELDS:
        return value
    if field == "evidence_report_available":
        if value not in ("True", "False"):
            errors.append(f"{iso}.{field}: expected True/False, got {value!r}")
        return value == "True"
    try:
        number = float(value)
    except ValueError:
        errors.append(f"{iso}.{field}: non-numeric value {value!r}")
        return None
    if not math.isfinite(number):
        errors.append(f"{iso}.{field}: non-finite value {value!r}")
        return None
    return int(number) if field in INT_FIELDS and number.is_integer() else number


def read_raw(path, keep, errors, excluded):
    """{iso: {year: value}} for economies only. Aggregates are counted, never kept."""
    out = defaultdict(dict)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            iso = (row.get("iso3") or "").strip() or (row.get("country_id") or "").strip()
            iso = iso.upper() if len(iso) == 3 and iso.isalpha() else ""
            if iso not in keep:
                excluded.add(iso or row.get("country_id", "?"))
                continue
            value = (row.get("value") or "").strip()
            if not value:
                continue
            try:
                year, number = int(str(row["date"])[:4]), float(value)
            except ValueError:
                errors.append(f"{path.name}: unparseable row {row}")
                continue
            if not math.isfinite(number):
                continue
            if year in out[iso] and out[iso][year] != number:
                errors.append(f"{path.name}: conflicting values for {iso} {year}")
            out[iso][year] = number
    return out


def latest(series, upto=WINDOW[1]):
    years = [y for y in series if y <= upto]
    return (max(years), series[max(years)]) if years else (None, None)


def scale_for(kind, values):
    if not values:
        return {"kind": kind, "domain": [0, 1]}
    if kind == "diverging":
        limit = nice(quantile([abs(v) for v in values], 0.95))
        return {"kind": "diverging", "domain": [-limit, 0, limit], "saturates": True}
    if kind == "log":
        return {"kind": "log", "domain": [max(1, min(values)), nice(max(values))]}
    if kind == "percent":
        return {"kind": "sequential", "domain": [0, 1], "format": "percent"}
    lo, hi = min(values), quantile(values, 0.95)
    top = min(nice(hi), max(values)) if hi > 0 else hi
    return {"kind": "sequential", "domain": [round(lo, 3), round(top, 3)], "saturates": top < max(values)}


# ---------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--package", required=True, type=Path)
    ap.add_argument("--sources", required=True, type=Path)
    ap.add_argument("--validation-out", type=Path, help="optional copy of the validation report")
    a = ap.parse_args()
    pkg, src = a.package.resolve(), a.sources.resolve()
    errors, warnings, discrepancies = [], [], []
    files = {
        "country_layers": pkg / "data/map/country_map_layers.csv",
        "catalog_csv": pkg / "data/map/layer_catalog.csv",
        "catalog_json": pkg / "data/map/layer_catalog.json",
        "pack_audit": pkg / "data/map/pack_audit.json",
        "evidence_reports": pkg / "data/evidence/pilot_evidence_reports.jsonl",
        "evidence_validation": pkg / "data/evidence/pilot_evidence_validation.json",
        "layer_notes": pkg / "docs/map_layers.md",
    }
    raw_files = {key: src / d / f"{code}.csv.gz" for key, (d, code) in RAW.items()}
    for name, path in {**files, **raw_files}.items():
        if not path.exists():
            sys.exit(f"missing input {name}: {path}")

    # ------------------------------------------------------------------ catalog
    catalog = json.loads(files["catalog_json"].read_text(encoding="utf-8"))
    with open(files["catalog_csv"], newline="", encoding="utf-8") as fh:
        catalog_csv = list(csv.DictReader(fh))
    ids = [layer["id"] for layer in catalog]
    if len(ids) != len(set(ids)):
        errors.append("layer catalog has duplicate ids")
    if ids != [row["id"] for row in catalog_csv]:
        errors.append("layer_catalog.csv and layer_catalog.json list different layers")
    for layer, row in zip(catalog, catalog_csv):
        for key in ("label", "unit", "palette", "type", "caveat"):
            if str(layer.get(key)) != row.get(key):
                errors.append(f"catalog mismatch for {layer['id']}.{key} between CSV and JSON")
        if layer["id"] not in SHORT_CAVEAT:
            errors.append(f"no short caveat for {layer['id']}")
        if layer["unit"] not in UNIT_SHORT:
            errors.append(f"no short unit for {layer['id']} ({layer['unit']!r})")
    for layer_id in list(PRIMARY) + MORE:
        if layer_id not in ids:
            errors.append(f"exposed layer {layer_id} is not in the layer catalog")

    # ------------------------------------------------------------------ package countries
    with open(files["country_layers"], newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        columns, rows = reader.fieldnames, list(reader)
    for layer_id in ids:
        if layer_id not in columns:
            errors.append(f"catalog layer {layer_id} has no column in country_map_layers.csv")
    countries = {}
    for row in rows:
        iso = row["iso3"].strip()
        if len(iso) != 3 or not iso.isalpha() or not iso.isupper():
            errors.append(f"invalid iso3 {iso!r}")
        if iso in countries:
            errors.append(f"duplicate iso3 {iso}")
        rec = {f: parse_cell(f, row[f], errors, iso) for f in columns if f != "iso3"}
        for f in PROBABILITY_FIELDS:
            if rec.get(f) is not None and not 0 <= rec[f] <= 1:
                errors.append(f"{iso}.{f}={rec[f]} outside [0, 1]")
        state = rec.get("gap_momentum_state")
        probs = {s: rec.get(f) for s, f in STATES.items()}
        if state is not None:
            if state not in STATES:
                errors.append(f"{iso}: unknown momentum state {state!r}")
            elif any(v is None for v in probs.values()):
                errors.append(f"{iso}: momentum state without all three probabilities")
            elif abs(sum(probs.values()) - 1) > 1e-6:
                errors.append(f"{iso}: momentum probabilities do not sum to 1")
            elif max(probs, key=probs.get) != state:
                discrepancies.append({"type": "momentum_state_not_highest_probability", "iso3": iso, "state": state,
                                      "highest_probability_state": max(probs, key=probs.get)})
        countries[iso] = rec
    audit = json.loads(files["pack_audit"].read_text(encoding="utf-8"))
    pkg_coverage = {i: sum(1 for c in countries.values() if c.get(i) is not None) for i in ids}
    for layer_id, expected in audit.get("coverage_by_layer", {}).items():
        if pkg_coverage.get(layer_id) != expected:
            errors.append(f"coverage for {layer_id}: {pkg_coverage.get(layer_id)} rows, package audit says {expected}")

    # ------------------------------------------------------------------ map join + economies
    codes = json.loads((ROOT / "src/data/researchCountryCodes.json").read_text(encoding="utf-8"))
    mapped = {v for v in codes.values() if v}
    keep = set(countries) | {p.stem for p in (ROOT / "public/data/mia").glob("???.json")}
    for iso in sorted(set(countries) - mapped):
        warnings.append(f"{iso} has data but no map feature (not drawn on the map)")

    # ------------------------------------------------------------------ raw sources
    excluded = set()
    raw = {key: read_raw(path, keep, errors, excluded) for key, path in raw_files.items()}

    def window_series(key):
        return {iso: {y: v for y, v in s.items() if WINDOW[0] <= y <= WINDOW[1]} for iso, s in raw[key].items()}

    def paired_gap(a_key, b_key, fn):
        """Same-year combination only; never fills a missing partner year."""
        out = defaultdict(dict)
        A, B = window_series(a_key), window_series(b_key)
        for iso in set(A) & set(B):
            for y in set(A[iso]) & set(B[iso]):
                out[iso][y] = fn(A[iso][y], B[iso][y])
        return out

    edu_gap = {iso: {y: v - 1 for y, v in s.items()} for iso, s in window_series("edu_gpi_secondary").items()}
    emp_gap = {iso: {y: v / 100 - 1 for y, v in s.items()} for iso, s in window_series("lfpr_ratio").items()}
    conv_gap = defaultdict(dict)
    for iso in set(edu_gap) & set(emp_gap):
        for y in set(edu_gap[iso]) & set(emp_gap[iso]):
            conv_gap[iso][y] = edu_gap[iso][y] - emp_gap[iso][y]
    series = {
        "education_gap_timeline": edu_gap,
        "employment_gap_timeline": emp_gap,
        "conversion_gap_timeline": conv_gap,
        "female_lfpr_timeline": window_series("lfpr_fe"),
        "female_vulnerable_employment_timeline": window_series("vuln_fe"),
        "rural_electricity_gap_timeline": paired_gap("elec_ur", "elec_ru", lambda u, r: u - r),
        "rural_clean_cooking_gap_timeline": paired_gap("cook_ur", "cook_ru", lambda u, r: u - r),
    }
    finance_waves = paired_gap("acct_fe", "acct_ma", lambda f, m: f - m)
    identity_waves = window_series("id_fe")

    def to_arrays(data, years):
        return {iso: [r4(s.get(y)) for y in years] for iso, s in sorted(data.items()) if s}

    timeline, layers_out = {}, []
    for spec in HISTORICAL:
        data = series[spec["id"]]
        all_years = sorted({y for s in data.values() for y in s})
        if not all_years:
            errors.append(f"{spec['id']}: no data")
            continue
        years = list(range(all_years[0], all_years[-1] + 1))  # every year in range; gaps stay null
        timeline[spec["id"]] = {"years": years, "values": to_arrays(data, years)}
        values = [v for s in data.values() for v in s.values()]
        if spec["type"] == "percentage" and not all(0 <= v <= 100 for v in values):
            errors.append(f"{spec['id']}: percentage outside 0-100")
        by_year = {y: sum(1 for s in data.values() if y in s) for y in years}
        layers_out.append({**{k: v for k, v in spec.items() if k != "scale"}, "recommended": True,
                           "display_label": spec["label"], "group": "historical", "temporal": "timeline",
                           "period": f"{years[0]}–{years[-1]} (observed or modelled years only)",
                           "years": [years[0], years[-1]], "scale": scale_for(spec["scale"], values),
                           "coverage": len(data), "coverage_by_year": by_year})
    for key, data in (("finance_gender_gap_pp", finance_waves), ("identity_female_pct", identity_waves)):
        waves = sorted({y for s in data.values() for y in s})
        timeline[key] = {"years": waves, "values": to_arrays(data, waves)}

    # ------------------------------------------------------------------ snapshot enrichment + checks
    time_tax = paired_gap("time_fe", "time_ma", lambda f, m: (f - m) * 24 / 100)  # % of 24h day -> hours/day
    visibility = {}
    for iso, rec in countries.items():
        y, v = latest(finance_waves.get(iso, {}))
        rec["finance_gender_gap_year"] = y
        if v is not None and rec.get("finance_gender_gap_pp") is not None and abs(v - rec["finance_gender_gap_pp"]) > 0.05:
            discrepancies.append({"type": "finance_latest_differs", "iso3": iso, "package": rec["finance_gender_gap_pp"],
                                  "raw": round(v, 3), "raw_year": y})
        y, v = latest(time_tax.get(iso, {}))
        rec["time_tax_year"] = y
        if (v is None) != (rec.get("time_tax_extra_hours_day") is None) or (v is not None and abs(v - rec["time_tax_extra_hours_day"]) > 0.01):
            discrepancies.append({"type": "time_tax_differs", "iso3": iso, "package": rec.get("time_tax_extra_hours_day"),
                                  "raw": None if v is None else round(v, 3), "raw_year": y})
        y, v = latest(identity_waves.get(iso, {}))
        if v is not None and (rec.get("identity_female_pct") is None or abs(v - rec["identity_female_pct"]) > 0.05):
            discrepancies.append({"type": "identity_package_not_latest_wave", "iso3": iso,
                                  "package": None if rec.get("identity_female_pct") is None else round(rec["identity_female_pct"], 3),
                                  "raw_latest": round(v, 3), "raw_year": y})
        rec["identity_female_pct_package"] = rec.get("identity_female_pct")
        rec["identity_female_pct"], rec["identity_female_pct_year"] = v, y  # latest genuine wave from the raw source
        # Country profile: separate measures, each with its own year and value type.
        profile = []
        for label, fe_key, ma_key, unit, vtype in PROFILE:
            fy, fv = latest(raw[fe_key].get(iso, {}))
            my, mv = latest(raw[ma_key].get(iso, {})) if ma_key else (None, None)
            if fv is not None or mv is not None:
                profile.append({"label": label, "female": r4(fv), "male": r4(mv) if my == fy else None,
                                "year": fy or my, "unit": unit, "value_type": vtype})
        rec["employment_quality"] = profile
        cells = observed = 0
        for key, start in VISIBILITY_SERIES:
            s = raw[key].get(iso, {})
            cells += WINDOW[1] - start + 1
            observed += sum(1 for y in s if start <= y <= WINDOW[1])
        edu_years = [y for y in raw["edu_gpi_secondary"].get(iso, {}) if WINDOW[0] <= y <= WINDOW[1]]
        vis = {"observed_education_years": len(edu_years),
               "latest_observed_education_year": max(edu_years) if edu_years else None,
               "observed_missing_share": round(1 - observed / cells, 4),
               "gender_disaggregated_observed": any(bool(raw[k].get(iso)) for k in ("edu_gpi_secondary", "edu_sec_fe", "mgmt_fe")),
               "rural_disaggregated_available": bool(raw["elec_ru"].get(iso))}
        rec.update(vis)
        visibility[iso] = vis
    for iso in sorted(keep - set(countries)):
        warnings.append(f"{iso} appears in the rural–urban data but not in the conversion package")

    # ------------------------------------------------------------------ package layer registry
    registry = []
    for layer in catalog:
        lid = layer["id"]
        values = [c[lid] for c in countries.values() if isinstance(c.get(lid), (int, float)) and not isinstance(c.get(lid), bool)]
        if layer["type"] == "probability":
            scale = scale_for("percent", values)
        elif layer["type"] == "categorical":
            scale = {"kind": "categorical", "categories": list(STATES), "probabilities": STATES}
        elif layer["type"] == "boolean":
            scale = {"kind": "categorical", "categories": [True, False]}
        elif lid in LOG:
            scale = scale_for("log", values)
        elif lid in DIVERGING:
            scale = scale_for("diverging", values)
        elif layer["type"] == "integer":
            scale = {"kind": "stepped", "domain": [min(values), max(values)]}
        else:
            scale = scale_for("sequential", values)
        temporal = "waves" if lid in ("finance_gender_gap_pp", "identity_female_pct") else "snapshot"
        entry = {**{k: layer[k] for k in ("id", "label", "question", "type", "unit", "palette", "direction", "source",
                                          "recommended", "caveat")},
                 "display_label": PRIMARY.get(lid, layer["label"]), "unit_short": UNIT_SHORT[layer["unit"]],
                 "short_caveat": SHORT_CAVEAT[lid],
                 "group": "primary" if lid in PRIMARY else "more" if lid in MORE else "registry",
                 "temporal": temporal, "period": PERIOD.get(lid),
                 "value_type": "model_output" if lid in MODEL_OUTPUTS else "observed",
                 "scale": scale, "coverage": sum(1 for c in countries.values() if c.get(lid) is not None)}
        if lid == "identity_female_pct":
            entry["source"] = "Global Findex / ID4D via World Bank (ID.OWN.TOTL.FE.ZS), latest genuine wave"
        if lid == "maternal_mortality_ratio":
            entry["value_type"] = "modelled"
        if temporal == "waves":
            entry["years"] = timeline[lid]["years"]
        if lid in ("finance_gender_gap_pp", "identity_female_pct", "time_tax_extra_hours_day"):
            entry["year_field"] = {"finance_gender_gap_pp": "finance_gender_gap_year",
                                   "identity_female_pct": "identity_female_pct_year",
                                   "time_tax_extra_hours_day": "time_tax_year"}[lid]
        registry.append(entry)
    for spec in VISIBILITY:
        values = [v[spec["id"]] for v in visibility.values()]
        scale = {"kind": "sequential", "domain": [0, 1], "format": "percent"} if spec["type"] == "share" else scale_for("sequential", values)
        registry.append({**{k: v for k, v in spec.items() if k != "scale"}, "recommended": True,
                         "display_label": spec["label"], "group": "more", "temporal": "snapshot",
                         "period": "Observed years, 1990–2024", "scale": scale, "coverage": len(values)})
    order = list(PRIMARY) + [s["id"] for s in HISTORICAL] + MORE + [s["id"] for s in VISIBILITY]
    layers_all = sorted(registry + layers_out, key=lambda l: order.index(l["id"]) if l["id"] in order else len(order))
    for layer in layers_all:
        if layer["temporal"] in ("timeline", "waves") and layer["id"] not in timeline:
            errors.append(f"{layer['id']} is time-based but has no timeline series")
    exposed = [l for l in layers_all if l["group"] != "registry"]

    # ------------------------------------------------------------------ evidence
    checks = json.loads((ROOT / "scripts/conversion_source_checks.json").read_text(encoding="utf-8"))
    evidence = {}
    for line in files["evidence_reports"].read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        report = json.loads(line)
        iso = report["country"]["iso3"]
        if iso not in countries:
            errors.append(f"evidence report {report['task_id']} refers to unknown iso3 {iso}")
        elif not countries[iso].get("evidence_report_available"):
            errors.append(f"evidence report for {iso} but evidence_report_available is not True")
        if iso in evidence:
            errors.append(f"more than one evidence report for {iso}")
        if report.get("causal_conclusion") is not False or len(report.get("mechanisms", [])) > 3:
            errors.append(f"evidence report {report['task_id']} violates causal_conclusion=false or <=3 mechanisms")
        evidence[iso] = report
    flagged = {iso for iso, c in countries.items() if c.get("evidence_report_available")}
    if flagged != set(evidence):
        errors.append(f"evidence flags {sorted(flagged)} do not match reports {sorted(evidence)}")
    cited = {e["url"] for r in evidence.values() for m in r["mechanisms"] for e in m["supporting_evidence"]} | \
            {e["url"] for r in evidence.values() for e in r["contradicting_or_complicating_evidence"]}
    for url in checks["notes"]:
        if url not in cited:
            warnings.append(f"source-check note for an uncited URL: {url}")

    validation = {"status": "failed" if errors else "passed", "errors": errors, "warnings": warnings,
                  "discrepancy_counts": {t: sum(1 for d in discrepancies if d["type"] == t) for t in sorted({d["type"] for d in discrepancies})},
                  "discrepancies": discrepancies}
    if a.validation_out:
        a.validation_out.parent.mkdir(parents=True, exist_ok=True)
        a.validation_out.write_text(json.dumps(validation, indent=2), encoding="utf-8")
    if errors:
        print(json.dumps({"errors": errors[:40]}, indent=2))
        sys.exit(f"validation failed with {len(errors)} error(s); nothing written")

    # ------------------------------------------------------------------ write
    DEST.mkdir(parents=True, exist_ok=True)

    def dump(name, obj):
        (DEST / name).write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":")), encoding="utf-8")
    dump("snapshot_atlas.json", {"countries": {iso: {k: r4(v) for k, v in c.items()} for iso, c in countries.items()}})
    dump("timeline_atlas.json", {"format": "values[ISO3][i] is the value for years[i]; null = no observation",
                                 "layers": timeline})
    dump("layers.json", {"layers": exposed, "registry_only": [l["id"] for l in layers_all if l["group"] == "registry"]})
    dump("coverage.json", {"layers": {l["id"]: {"countries": l["coverage"], "by_year": l.get("coverage_by_year")} for l in exposed},
                           "countries": visibility})
    dump("evidence_reports.json", {"label": "Contextual evidence — not causal attribution", "reports": evidence,
                                   "source_checks": {"checked_on": checks["checked_on"], "notes": checks["notes"]}})
    shutil.copyfile(files["layer_notes"], DEST / "LAYER_NOTES.md")
    provenance = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "Web_Design/scripts/build_conversion_web_data.py",
        "inputs": {
            "conversion_package": {name: {"path": str(p.relative_to(pkg)), "sha256": sha256(p)} for name, p in files.items()},
            "raw_archive": {"repository": "ErHxyun/Carolina-Data-Challenge-2026", "commit": RAW_COMMIT,
                            "path": "Graduate_Dataset/all_sources",
                            "files": {f"{d}/{code}.csv.gz": sha256(raw_files[k]) for k, (d, code) in RAW.items()}},
        },
        "selected_raw_indicators": {code: SELECTION_REASONS.get(code, "Partner series (female/male or rural/urban) of a selected indicator.")
                                    for _, code in RAW.values()},
        "economies": len(keep), "aggregate_codes_excluded": len(excluded),
        "row_counts": {"countries": len(countries), "evidence_reports": len(evidence)},
        "layer_counts": {"exposed": len(exposed), "primary": sum(l["group"] == "primary" for l in exposed),
                         "historical": sum(l["group"] == "historical" for l in exposed),
                         "more": sum(l["group"] == "more" for l in exposed),
                         "timeline": sum(l["temporal"] == "timeline" for l in exposed),
                         "waves": sum(l["temporal"] == "waves" for l in exposed),
                         "snapshot": sum(l["temporal"] == "snapshot" for l in exposed),
                         "registry_only": len(layers_all) - len(exposed)},
        "rules": ["ISO3 economies only; World Bank aggregates removed", "actual observation years preserved",
                  "missing values are null", "no interpolation, forward/backward fill or averaging",
                  "combined series use same-year pairs only", "ILO/WHO modelled series are labelled modelled"],
        "validation": {k: v for k, v in validation.items() if k != "discrepancies"},
        "package_evidence_validation": json.loads(files["evidence_validation"].read_text("utf-8")),
    }
    (DEST / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    sizes = {p.name: p.stat().st_size for p in DEST.glob("*.json")}
    print(f"Wrote {len(exposed)} layers ({provenance['layer_counts']}), {len(countries)} countries, "
          f"{len(evidence)} evidence reports. Sizes: {sizes}")
    print(f"warnings: {len(warnings)}; discrepancies: {validation['discrepancy_counts']}")


if __name__ == "__main__":
    main()
