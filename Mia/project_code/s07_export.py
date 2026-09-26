"""
Step 7 - Hand-off package for teammates (UI/UX + LLM / multi-agent).

  outputs/handoff/
    ui/countries.json          one object per country: headline metrics, numeric, with CIs + flags
    ui/trajectories.json       per country x dimension: years, rural/urban women median + 90% band
    ui/indicators.json         observed indicator values (%, years) for rural vs urban women, by year
    ui/global_summary.json     headline numbers for landing page / key-findings cards
    ui/early_warning.json      2024->2027 risk list + model performance
    llm/findings.jsonl         every statistical finding as a structured, citable fact
    llm/prompts.jsonl          evidence-investigation prompts (copied from outputs/evidence)
    llm/agent_tools.py         plain-Python "tools" an agent can call (country profile, findings, ...)
    llm/tool_schemas.json      JSON schemas for those tools (Anthropic / OpenAI tool format)
    DATA_DICTIONARY.md         field definitions + what may / may not be claimed
"""
import json
import shutil

import numpy as np
import pandas as pd

import config as C
import latent as L
from common import country_table

MET, EW = C.OUT_DIR / "metrics", C.OUT_DIR / "early_warning"
HO = C.OUT_DIR / "handoff"
UI, LLM = HO / "ui", HO / "llm"
for d in (UI, LLM):
    d.mkdir(parents=True, exist_ok=True)
YEAR = 2021

DISPLAY = {
    "edu_years": ("Years of schooling (age 17+)", "years"), "enrol_6_16": ("School enrolment, age 6-16", "%"),
    "emp_to_pop": ("Employment-to-population", "%"), "nonag_wage_emp": ("Non-farm wage employment", "%"),
    "work_contract": ("Workers with a contract", "%"), "informal_job": ("Formal (non-informal) jobs", "%"),
    "social_security": ("Workers with social security", "%"), "nonag_emp_women": ("Women in non-farm work (direct)", "%"),
    "account": ("Has an account", "%"), "fi_account": ("Bank / FI account", "%"), "saved_formal": ("Saved formally", "%"),
    "borrow_formal": ("Borrowed formally", "%"), "debit_card": ("Owns a debit card", "%"),
    "emergency_funds": ("Can raise emergency funds in 30 days", "%"), "own_mobile": ("Owns a mobile phone", "%"),
    "digital_account": ("Digitally enabled account", "%"), "digital_payment": ("Made/received a digital payment", "%"),
    "online_id": ("Has an online digital ID", "%"), "id_ownership": ("Owns a foundational ID", "%"),
    "health_insur": ("Workers with health insurance", "%"), "basic_water": ("Basic drinking water", "%"),
    "basic_sanit": ("Basic sanitation", "%"), "handwashing": ("Handwashing facility", "%"),
    "menstrual_private": ("Private place to wash/change (direct)", "%"),
    "menstrual_materials": ("Uses menstrual materials (direct)", "%"),
    "electricity": ("Electricity access", "%"), "clean_cooking": ("Clean cooking fuel", "%"),
    "safe_water": ("Safely managed water", "%"),
}


def _f(x, nd=2):
    """JSON-safe float."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(x) else round(x, nd)


def build_countries():
    ct = country_table()
    dl = pd.read_csv(MET / "opportunity_delay.csv")
    d = dl[dl.year == YEAR]
    pwc = pd.read_csv(MET / "progress_without_convergence.csv")
    hl = pd.read_csv(MET / "inequality_half_life.csv")
    dv = pd.read_csv(MET / "divergence_point.csv")
    lk = pd.read_csv(MET / "leakage_edu_emp_by_country.csv").set_index("iso")
    ip = pd.read_csv(MET / "intersectional_penalty_by_country.csv").set_index("iso")
    dtw = pd.read_csv(MET / "dtw_analogues.csv").set_index("iso")
    ew = pd.read_csv(sorted(EW.glob("early_warning_*.csv"))[-1]).set_index("iso")
    summ = pd.read_csv(C.OUT_DIR / "country_summary.csv").set_index("iso")
    out = []
    for iso in summ.index:
        c = {"iso": iso, "name": ct.name.get(iso, iso), "region": ct.region.get(iso),
             "meaningful_gap": bool(summ.loc[iso, "meaningful_gap"]),
             "gap_overall_2021": _f(summ.loc[iso, f"gap_Overall_{YEAR}"]), "delay_2021": {}, "progress_2010_2020": {},
             "half_life": {}, "change_points": {}}
        for dim in ["Overall"] + C.TRAJECTORY_DIMS:
            r = d[(d.dimension == dim) & (d.iso == iso)]
            if len(r):
                r = r.iloc[0]
                c["delay_2021"][dim] = {"median": _f(r.delay_median, 1), "q05": _f(r.delay_q05, 1), "q95": _f(r.delay_q95, 1),
                                        "is_lower_bound": bool(r.delay_is_lower_bound),
                                        "extended_median": _f(r.delay_ext_median, 1),
                                        "years_to_nearest_obs": _f(r.years_to_nearest_obs, 0)}
            r = pwc[(pwc.dimension == dim) & (pwc.iso == iso) & (pwc.window == "2010-2020")]
            if len(r):
                r = r.iloc[0]
                c["progress_2010_2020"][dim] = {"label": r.label, "p_pwc": _f(r.p_pwc), "p_converging": _f(r.p_converging),
                                                "d_rural": _f(r.dZ_rural_median), "d_urban": _f(r.dZ_urban_median),
                                                "d_gap": _f(r.dGap_median)}
            r = hl[(hl.dimension == dim) & (hl.iso == iso)]
            if len(r):
                r = r.iloc[0]
                c["half_life"][dim] = {"verdict": r.verdict, "p_convergence": _f(r.p_convergence),
                                       "median": _f(r.half_life_median, 1), "q05": _f(r.half_life_q05, 1),
                                       "q95": _f(r.half_life_q95, 1)}
        for dim in ["Health", "Infrastructure", "Overall"]:
            r = dv[(dv.dimension == dim) & (dv.iso == iso)]
            if len(r) and not r.iloc[0].type.startswith("No clear"):
                r = r.iloc[0]
                c["change_points"][dim] = {"type": r.type, "window": [int(r.window_start), int(r.window_end)],
                                           "p_window": _f(r.p_window), "p_change_point": _f(r.p_change_point)}
        if iso in lk.index:
            c["edu_to_emp_leakage"] = {"Lambda": _f(lk.loc[iso, "Lambda_median"], 3), "p_weaker_for_rural": _f(lk.loc[iso, "p_Lambda_gt_0"])}
        if iso in ip.index:
            c["intersectional_wage"] = {"I": _f(ip.loc[iso, "I_median"], 3), "q05": _f(ip.loc[iso, "I_q05"], 3),
                                        "q95": _f(ip.loc[iso, "I_q95"], 3), "p_rural_penalty_larger": _f(ip.loc[iso, "p_I_gt_0"])}
        if iso in dtw.index:
            c["historical_analogues"] = {"list": dtw.loc[iso, "analogues"].split("; "),
                                         "share_escaped": _f(dtw.loc[iso, "share_analogues_escaped"])}
        if iso in ew.index:
            c["early_warning"] = {"p_delay_widens_2024_2027": _f(ew.loc[iso, "p_widen"]),
                                  "p_logit": _f(ew.loc[iso, "p_widen_logit"]), "p_lgbm": _f(ew.loc[iso, "p_widen_lgbm"])}
        out.append(c)
    json.dump(out, open(UI / "countries.json", "w"), indent=1)
    return out


def build_trajectories():
    res = {}
    for dim in ["Overall"] + C.TRAJECTORY_DIMS:
        d = L.load(dim)
        isos = sorted(set(d["iso"]))
        G = L.groups(dim, isos)
        sr, su = L.support(dim, isos, "RW"), L.support(dim, isos, "UW")
        q = {g: np.nanquantile(G[g], [0.05, 0.5, 0.95], axis=0) for g in ("RW", "UW")}
        for i, iso in enumerate(isos):
            if np.isnan(q["RW"][1, i]).all() or np.isnan(q["UW"][1, i]).all():
                continue
            res.setdefault(iso, {})[dim] = {
                "rural_women": {k: [_f(v) for v in q["RW"][j, i]] for j, k in enumerate(["q05", "median", "q95"])},
                "urban_women": {k: [_f(v) for v in q["UW"][j, i]] for j, k in enumerate(["q05", "median", "q95"])},
                "observed_year": [bool(a > 0 or b > 0) for a, b in zip(sr[i], su[i])]}
    json.dump({"years": [int(y) for y in L.years()], "unit": "latent opportunity (relative; compare RW vs UW only)",
               "countries": res}, open(UI / "trajectories.json", "w"))


def build_indicators():
    p = pd.read_csv(C.OUT_DIR / "panel_long.csv", usecols=["iso", "year", "group", "value", "indicator", "dimension", "kind"])
    p = p[p.group.isin(["RW", "UW"])]
    w = p.pivot_table(index=["iso", "indicator", "dimension", "kind", "year"], columns="group", values="value").reset_index()
    res = {}
    for (iso, ind), g in w.groupby(["iso", "indicator"]):
        name, unit = DISPLAY.get(ind, (ind, ""))
        scale = 100 if unit == "%" else 1
        res.setdefault(iso, []).append({
            "indicator": ind, "label": name, "unit": unit, "dimension": g.dimension.iloc[0],
            "source_type": {"marg": "estimated (rural x female approximation)", "hh": "household-level (same for women and men)",
                            "direct": "direct measurement"}[g.kind.iloc[0]],
            "years": g.year.astype(int).tolist(),
            "rural_women": [_f(v * scale, 1) for v in g.get("RW", pd.Series([np.nan] * len(g)))],
            "urban_women": [_f(v * scale, 1) for v in g.get("UW", pd.Series([np.nan] * len(g)))]})
    json.dump(res, open(UI / "indicators.json", "w"))


def build_global(countries):
    dl = pd.read_csv(MET / "opportunity_delay.csv")
    d = dl[dl.year == YEAR]
    mg = {c["iso"] for c in countries if c["meaningful_gap"]}
    delays = {}
    for dim in ["Education", "Employment", "Health", "Infrastructure", "Overall"]:
        x = d[(d.dimension == dim) & d.iso.isin(mg)]
        delays[dim] = {"n_countries": int(len(x)), "share_beyond_record": _f(x.delay_is_lower_bound.mean()),
                       "median_delay_measurable": _f(x[~x.delay_is_lower_bound].delay_median.median(), 1)}
    e = d[d.dimension == "Education"].set_index("iso"); j = d[d.dimension == "Employment"].set_index("iso")
    both = e.index.intersection(j.index)
    pwc = pd.read_csv(MET / "progress_without_convergence.csv")
    p10 = pwc[pwc.window == "2010-2020"]
    hl = pd.read_csv(MET / "inequality_half_life.csv"); ho = hl[hl.dimension == "Overall"]
    dv = pd.read_csv(MET / "divergence_point.csv")
    lk = pd.read_csv(MET / "progress_leakage.csv")
    ip = pd.read_csv(MET / "intersectional_penalty_summary.csv")
    perf = pd.read_csv(EW / "ew_performance.csv")
    val = pd.read_csv(C.OUT_DIR / "validation_rural_women.csv").set_index("method")
    g = {
        "headline": "Rural women have caught up on schooling far faster than on work.",
        "headline_year": YEAR,
        "opportunity_delay": delays,
        "share_countries_employment_delay_gt_education": _f((j.loc[both].delay_ext_median > e.loc[both].delay_ext_median).mean()),
        "progress_without_convergence_2010_2020": {dim: {k: int(v) for k, v in p10[p10.dimension == dim].label.value_counts().items()}
                                                   for dim in p10.dimension.unique()},
        "pwc_countries_overall_2010_2020": sorted(p10[(p10.dimension == "Overall") & (p10.label == "Progress Without Convergence")].iso),
        "half_life_overall": {"verdicts": {k: int(v) for k, v in ho.verdict.value_counts().items()},
                              "median_half_life_years": _f(ho.half_life_median.median(), 1)},
        "change_points": {dim: {k: int(v) for k, v in dv[dv.dimension == dim].type.value_counts().items()} for dim in dv.dimension.unique()},
        "progress_leakage": [{"link": r.link, "Lambda": _f(r.Lambda_median, 3), "ci90": [_f(r.Lambda_q05, 3), _f(r.Lambda_q95, 3)],
                              "p_weaker_for_rural": _f(r.p_Lambda_gt_0)} for r in lk.itertuples()],
        "intersectional_penalty": [{"scope": r.scope, "I": _f(r.I_median, 3), "ci90": [_f(r.I_q05, 3), _f(r.I_q95, 3)],
                                    "p_rural_penalty_larger": _f(r.p_I_gt_0)} for r in ip.itertuples()],
        "early_warning_performance": [{"model": r.model, "auc": _f(r.auc), "pr_auc": _f(r.pr_auc), "brier": _f(r.brier), "n": int(r.n)}
                                      for r in perf.itertuples()],
        "rural_women_approximation_validation": {"mae": _f(val.loc["RW_logit", "mae"], 3), "corr": _f(val.loc["RW_logit", "corr"], 3),
                                                 "n_surveys": int(val.loc["RW_logit", "n"])},
    }
    json.dump(g, open(UI / "global_summary.json", "w"), indent=1)
    return g


def build_early_warning():
    ew = pd.read_csv(sorted(EW.glob("early_warning_*.csv"))[-1])
    ct = country_table()
    shap = pd.read_csv(EW / "ew_shap_importance.csv", index_col=0).iloc[:, 0]
    json.dump({"horizon": "2024 -> 2027", "question": "Will rural women's Opportunity Delay widen over the next 3 years?",
               "countries": [{"iso": r.iso, "name": ct.name.get(r.iso, r.iso), "region": r.region, "p_widen": _f(r.p_widen),
                              "current_delay_filtered": _f(r.delay_f, 1), "gap": _f(r.gap_Overall)} for r in ew.itertuples()],
               "top_drivers_mean_abs_shap": {k: _f(v, 3) for k, v in shap.head(10).items()},
               "performance": pd.read_csv(EW / "ew_performance.csv").round(3).to_dict(orient="records")},
              open(UI / "early_warning.json", "w"), indent=1)


def build_findings(countries):
    """Every finding as one self-contained, citable fact for an LLM / agent (no free text to parse)."""
    rows = []
    for c in countries:
        base = {"iso": c["iso"], "country": c["name"], "region": c["region"], "meaningful_gap": c["meaningful_gap"]}
        for dim, v in c["delay_2021"].items():
            if v["median"] is None:
                continue
            txt = (f"In {YEAR}, rural women's {dim.lower()} opportunity trajectory most resembles where urban women were "
                   + (f"more than {v['median']:.0f} years earlier (beyond the 1990 data record)" if v["is_lower_bound"]
                      else f"about {v['median']:.1f} years earlier (90% CI {v['q05']:.1f}-{v['q95']:.1f})") + ".")
            rows.append({**base, "finding_type": "opportunity_delay", "dimension": dim, "year": YEAR, "statement": txt,
                         "evidence_strength": "lower_bound" if v["is_lower_bound"] else "estimate_with_ci", **v})
        for dim, v in c["progress_2010_2020"].items():
            if v["label"] in ("Progress Without Convergence", "Converging progress", "No rural progress"):
                rows.append({**base, "finding_type": "progress_pattern", "dimension": dim, "period": "2010-2020",
                             "statement": f"{dim} 2010-2020: {v['label']} (P(progress without convergence)={v['p_pwc']}).", **v})
        for dim, v in c["half_life"].items():
            rows.append({**base, "finding_type": "half_life", "dimension": dim,
                         "statement": (f"{dim}: converging with P={v['p_convergence']}, median half-life {v['median']} years "
                                       f"(90% CI {v['q05']}-{v['q95']})." if v["median"] is not None
                                       else f"{dim}: {v['verdict']} (P(convergence)={v['p_convergence']})."), **v})
        for dim, v in c["change_points"].items():
            rows.append({**base, "finding_type": "change_point", "dimension": dim, "period": f"{v['window'][0]}-{v['window'][1]}",
                         "statement": f"{dim}: {v['type']} around {v['window'][0]}-{v['window'][1]} (P(window)={v['p_window']}).", **v})
        if "early_warning" in c:
            rows.append({**base, "finding_type": "early_warning", "dimension": "Overall", "period": "2024-2027",
                         "statement": f"Probability that the delay widens 2024-2027: {c['early_warning']['p_delay_widens_2024_2027']}.",
                         **c["early_warning"]})
    with open(LLM / "findings.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return len(rows)


TOOLS_PY = r'''"""
Plain-Python tools over the hand-off files, ready to wrap as LLM tool calls / agent skills.
Only reads JSON in ../ui and ./findings.jsonl - no model or heavy dependency needed.

    from agent_tools import get_country_profile, get_findings, compare_countries, list_high_risk, get_global_summary
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_UI = HERE.parent / "ui"
_C = {c["iso"]: c for c in json.load(open(_UI / "countries.json"))}
_F = [json.loads(l) for l in open(HERE / "findings.jsonl")]
_NAME = {c["name"].lower(): i for i, c in _C.items()}


def _iso(country):
    c = country.strip()
    return c.upper() if c.upper() in _C else _NAME.get(c.lower())


def get_country_profile(country: str) -> dict:
    """All headline metrics for one country (ISO3 code or World Bank name)."""
    iso = _iso(country)
    return _C.get(iso, {"error": f"unknown country: {country}"})


def get_findings(country: str = None, finding_type: str = None, dimension: str = None, limit: int = 50) -> list:
    """Structured findings filtered by country / type (opportunity_delay, progress_pattern, half_life,
    change_point, early_warning) / dimension (Overall, Education, Employment, Health, Infrastructure)."""
    iso = _iso(country) if country else None
    out = [f for f in _F if (iso is None or f["iso"] == iso) and (finding_type is None or f["finding_type"] == finding_type)
           and (dimension is None or f["dimension"] == dimension)]
    return out[:limit]


def compare_countries(countries: list, dimension: str = "Overall") -> list:
    """Side-by-side delay, progress pattern and half-life for several countries."""
    rows = []
    for c in countries:
        p = get_country_profile(c)
        if "error" in p:
            rows.append(p); continue
        rows.append({"iso": p["iso"], "name": p["name"], "delay_2021": p["delay_2021"].get(dimension),
                     "progress_2010_2020": p["progress_2010_2020"].get(dimension), "half_life": p["half_life"].get(dimension),
                     "early_warning": p.get("early_warning")})
    return rows


def list_high_risk(top: int = 10, region: str = None) -> list:
    """Countries most likely to see rural women's delay widen 2024-2027."""
    ew = json.load(open(_UI / "early_warning.json"))["countries"]
    ew = [c for c in ew if region is None or c["region"] == region]
    return sorted(ew, key=lambda c: -(c["p_widen"] or 0))[:top]


def get_global_summary() -> dict:
    """Headline cross-country results (delays by dimension, leakage, intersectional penalty, model performance)."""
    return json.load(open(_UI / "global_summary.json"))


if __name__ == "__main__":
    print(json.dumps(get_country_profile("India")["delay_2021"], indent=1))
    print(list_high_risk(3))
'''

SCHEMAS = [
    {"name": "get_country_profile", "description": "All headline metrics (opportunity delay, progress pattern, half-life, change points, leakage, intersectional wage penalty, historical analogues, early-warning risk) for one country.",
     "input_schema": {"type": "object", "properties": {"country": {"type": "string", "description": "ISO3 code or World Bank country name"}}, "required": ["country"]}},
    {"name": "get_findings", "description": "Structured statistical findings, each with a plain-language statement and its uncertainty. Filter by country, finding_type and dimension.",
     "input_schema": {"type": "object", "properties": {
         "country": {"type": "string"},
         "finding_type": {"type": "string", "enum": ["opportunity_delay", "progress_pattern", "half_life", "change_point", "early_warning"]},
         "dimension": {"type": "string", "enum": ["Overall", "Education", "Employment", "Health", "Infrastructure"]},
         "limit": {"type": "integer", "default": 50}}}},
    {"name": "compare_countries", "description": "Side-by-side comparison of several countries on one dimension.",
     "input_schema": {"type": "object", "properties": {"countries": {"type": "array", "items": {"type": "string"}},
                                                        "dimension": {"type": "string", "default": "Overall"}}, "required": ["countries"]}},
    {"name": "list_high_risk", "description": "Countries with the highest predicted probability that rural women's opportunity delay widens 2024-2027.",
     "input_schema": {"type": "object", "properties": {"top": {"type": "integer", "default": 10}, "region": {"type": "string"}}}},
    {"name": "get_global_summary", "description": "Cross-country headline results and model performance.",
     "input_schema": {"type": "object", "properties": {}}},
]

DICT_MD = """# Hand-off data dictionary

Generated by `s07_export.py` from the pipeline outputs. Re-run `python run_all.py --from 7` after any change upstream.

## Who uses what

| Teammate | Files | Use |
|---|---|---|
| UI / visualisation | `ui/countries.json`, `ui/trajectories.json`, `ui/indicators.json`, `ui/global_summary.json`, `ui/early_warning.json`, `../figures/*.png` | country pages, maps, trajectory charts, key-finding cards, risk list |
| LLM / multi-agent | `llm/findings.jsonl`, `llm/prompts.jsonl`, `llm/agent_tools.py`, `llm/tool_schemas.json`, `ui/global_summary.json` | grounding facts, evidence-investigation prompts, tool calls |
| Modelling | `../early_warning/ew_dataset.csv`, `../metrics/*.csv`, `../latent/*.npz` | re-train / extend the early-warning model, new metrics |

## ui/countries.json  (list, one object per country)
- `iso`, `name`, `region` (6 continents; "North America" includes Central America and the Caribbean)
- `meaningful_gap` - **filter on this for rankings/maps**. False = rural and urban women roughly at parity (gap < 0.2); a "delay" there is noise.
- `gap_overall_2021` - urban minus rural women, latent units. Use only for ordering or colour, never as a headline number.
- `delay_2021[dim]` - Opportunity Delay in **years**: `median`, `q05`, `q95` (90% credible interval).
  - `is_lower_bound = true` -> show as **"> {median} years"**: rural women are below every urban level since 1990.
  - `extended_median` - extrapolated beyond 1990 (assumption, capped 60). Model input only; do not display as a finding.
  - `years_to_nearest_obs` - 0 = survey that year; large values = interpolated. Consider greying out anything > 5.
- `progress_2010_2020[dim].label` - one of `Converging progress`, `Progress Without Convergence`, `No rural progress`, `Uncertain`, `At parity`, `Insufficient data`.
- `half_life[dim]` - `verdict` (`Converging` / `No strong evidence of convergence` / `Diverging`); `median`/`q05`/`q95` in years (only when Converging; `q95` may be null = unbounded).
- `change_points[dim]` - only present when a change point exists: `type`, `window` [start, end], `p_window`.
- `edu_to_emp_leakage` - `Lambda` > 0 means education converts to jobs less strongly for rural women; `p_weaker_for_rural` = P(Lambda > 0).
- `intersectional_wage` - from direct wage ratios; `I` > 0 means the gender pay penalty is larger in rural areas.
- `historical_analogues.list` - "ISO@year:outcome" DTW matches; `share_escaped`.
- `early_warning.p_delay_widens_2024_2027` - average of the logistic and LightGBM probabilities.

## ui/trajectories.json
`years` (1990-2024) plus `countries[iso][dim].rural_women|urban_women.{q05,median,q95}` (arrays aligned to `years`), and `observed_year` (true where a survey/estimate exists).
Plot rural vs urban women as two lines with bands; **hide the y-axis numbers or label them "relative opportunity"** - the scale has no absolute meaning. Dimensions: Overall, Education, Employment, Health, Infrastructure.

## ui/indicators.json
`[iso] -> list of indicators` with `label`, `unit` (% or years), `source_type`, `years`, `rural_women`, `urban_women`. These are the interpretable raw numbers for tooltips ("62% of rural women own a phone vs 81% of urban women").
`source_type` must be shown or footnoted: *estimated* values come from the rural x female approximation (validated: mean error 1.3 pp).

## llm/findings.jsonl
One JSON object per finding: `iso`, `country`, `finding_type`, `dimension`, `year`/`period`, `statement` (plain English, uncertainty included), plus the numeric fields.
Ground every generated sentence in a `statement`; quote the CI or probability that comes with it.

## Rules for any text or chart built on these results
1. Delays are **"trajectory resembles urban women N years earlier"**, not "each rural woman is N years behind".
2. Always show the uncertainty (CI or probability); never a single decimal without it.
3. `is_lower_bound` delays are "> N years".
4. Finance / Digital / Resilience are 2024 snapshots - no trends over time.
5. Escapers, SHAP and change points are associational - never "X caused convergence".
6. The early-warning model is AUC 0.87 on held-out years but 0.65 on unseen regions; present it as a screening signal.
7. Rural-women values are model-based estimates except the three `direct` indicators and the wage ratios.
"""


def main():
    countries = build_countries()
    build_trajectories()
    build_indicators()
    build_global(countries)
    build_early_warning()
    n = build_findings(countries)
    shutil.copy(C.OUT_DIR / "evidence" / "prompts.jsonl", LLM / "prompts.jsonl")
    (LLM / "agent_tools.py").write_text(TOOLS_PY)
    json.dump(SCHEMAS, open(LLM / "tool_schemas.json", "w"), indent=1)
    (HO / "DATA_DICTIONARY.md").write_text(DICT_MD)
    print(f"handoff: {len(countries)} countries, {n} findings -> {HO}")


if __name__ == "__main__":
    main()
