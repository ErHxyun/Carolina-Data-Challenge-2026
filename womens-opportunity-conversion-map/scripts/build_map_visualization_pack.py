import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "map_visualization_pack"
OUT.mkdir(parents=True, exist_ok=True)


def read(rel):
    return pd.read_csv(ROOT / rel)


base = read("outputs/descriptive_opportunity_stages/country_stage_profiles.csv")
base = base.sort_values(["iso3", "country"]).drop_duplicates("iso3", keep="last")

# Core transformations are continuous; the map can use a diverging or sequential scale
# without introducing arbitrary country-stage cutoffs.
base["education_employment_conversion_gap_z"] = (
    base["education_advantage_z"] - base["employment_advantage_z"]
)
# Dispersion is not interpretable from only one or two observed domains. Preserve
# missingness instead of coloring those countries as perfectly synchronized.
base.loc[base["core_domains_observed"] < 3, "desynchronization_sd"] = np.nan
base["finance_gender_gap_pp"] = base["finance_advantage_raw"]
base["digital_gender_gap_pp"] = base["digital_advantage_raw"]
base["employment_gender_gap_z"] = base["employment_advantage_z"]
base["education_gender_gap_z"] = base["education_advantage_z"]
base["missing_core_domains"] = 4 - base["core_domains_observed"]
base["latest_core_observation_year"] = base[
    ["education_year", "employment_year", "finance_year", "digital_year"]
].max(axis=1)
base["oldest_core_observation_year"] = base[
    ["education_year", "employment_year", "finance_year", "digital_year"]
].min(axis=1)
base["core_year_spread"] = base["latest_core_observation_year"] - base["oldest_core_observation_year"]
base.loc[base["core_domains_observed"] < 2, "core_year_spread"] = np.nan


resid = read("outputs/conversion_evidence_agent/conversion_residual_candidates.csv")[
    [
        "iso3",
        "expected_employment_advantage",
        "conversion_residual",
        "residual_percentile",
    ]
].drop_duplicates("iso3")
base = base.merge(resid, on="iso3", how="left")

div = read("outputs/conversion_evidence_agent/education_employment_divergence_candidates.csv")[
    [
        "iso3",
        "education_gap_improvement_sd",
        "employment_gap_improvement_sd",
        "conversion_shortfall",
        "education_start_year",
        "education_end_year",
        "employment_start_year",
        "employment_end_year",
    ]
].drop_duplicates("iso3")
base = base.merge(div, on="iso3", how="left")

hmm = read("outputs/predictive_v2/hmm_current_state.csv").sort_values("year").drop_duplicates("iso3", keep="last")
hmm = hmm.rename(
    columns={
        "year": "hmm_year",
        "hmm_state": "gap_momentum_state",
        "p_Closing": "prob_gap_closing",
        "p_Flat": "prob_gap_flat",
        "p_Widening": "prob_gap_widening",
    }
)
base = base.merge(hmm, on="iso3", how="left")

fpt = read("outputs/opportunity_gap_model/first_passage_gap_estimates.csv").drop_duplicates("iso3")
fpt = fpt.rename(
    columns={
        "as_of_year": "fpt_as_of_year",
        "prob_halve_by_2030": "prob_employment_gap_halves_by_2030",
        "prob_halve_within_10y": "prob_employment_gap_halves_within_10y",
        "median_first_passage_years": "median_years_to_half_employment_gap",
        "prob_not_reached_15y": "prob_gap_not_halved_within_15y",
    }
)
base = base.merge(
    fpt[
        [
            "iso3",
            "fpt_as_of_year",
            "current_employment_gap_sd",
            "prob_employment_gap_halves_by_2030",
            "prob_employment_gap_halves_within_10y",
            "median_years_to_half_employment_gap",
            "prob_gap_not_halved_within_15y",
        ]
    ],
    on="iso3",
    how="left",
)

delays = read("outputs/development_wait_analysis/latest_domain_delays.csv").sort_values("year")
delay_rows = []
for iso3, group in delays.groupby("iso3"):
    row = {"iso3": iso3, "delay_latest_year": int(group["year"].max())}
    for column in ["education", "employment", "joint", "desynchronization_sd_years"]:
        values = group.loc[group[column].notna(), column]
        row[f"development_delay_{column}_years"] = values.iloc[-1] if len(values) else np.nan
    delay_rows.append(row)
base = base.merge(pd.DataFrame(delay_rows), on="iso3", how="left")

rural = read("outputs/rural_urban/gap_trend_by_country.csv")
rural = rural[rural["series"].eq("infra_gap")].sort_values(["iso3", "y1"]).drop_duplicates("iso3", keep="last")
rural = rural.rename(
    columns={
        "region_name": "region",
        "income_level_name": "income_group",
        "p_shrinking": "prob_rural_time_tax_gap_shrinking",
        "verdict": "rural_time_tax_gap_trend",
        "gap_last": "rural_time_tax_gap_latest_pp",
        "y1": "rural_time_tax_gap_year",
    }
)
base = base.merge(
    rural[
        [
            "iso3",
            "region",
            "income_group",
            "prob_rural_time_tax_gap_shrinking",
            "rural_time_tax_gap_trend",
            "rural_time_tax_gap_latest_pp",
            "rural_time_tax_gap_year",
        ]
    ],
    on="iso3",
    how="left",
)

# Human-reviewed pilot evidence becomes a separate inspection layer.
pilot_path = ROOT / "outputs/conversion_evidence_agent/pilot_evidence_reports.jsonl"
pilot_rows = []
if pilot_path.exists():
    for line in pilot_path.read_text().splitlines():
        report = json.loads(line)
        pilot_rows.append(
            {
                "iso3": report["country"]["iso3"],
                "evidence_report_available": True,
                "evidence_confidence": report["overall_confidence"],
                "evidence_mechanism_1": report["mechanisms"][0]["mechanism"] if report["mechanisms"] else None,
                "evidence_mechanism_count": len(report["mechanisms"]),
                "complicating_evidence_count": len(report["contradicting_or_complicating_evidence"]),
            }
        )
pilot = pd.DataFrame(pilot_rows)
if len(pilot):
    base = base.merge(pilot, on="iso3", how="left")
else:
    base["evidence_report_available"] = False
base["evidence_report_available"] = base["evidence_report_available"].fillna(False).astype(bool)


keep = [
    "iso3",
    "country",
    "region",
    "income_group",
    "education_gender_gap_z",
    "employment_gender_gap_z",
    "education_employment_conversion_gap_z",
    "finance_gender_gap_pp",
    "digital_gender_gap_pp",
    "identity_female_pct",
    "time_tax_extra_hours_day",
    "maternal_mortality_ratio",
    "opportunity_level_z",
    "desynchronization_sd",
    "synchronization_adjusted_score",
    "core_domains_observed",
    "missing_core_domains",
    "core_year_spread",
    "latest_core_observation_year",
    "trajectory_state",
    "archetype",
    "expected_employment_advantage",
    "conversion_residual",
    "residual_percentile",
    "education_gap_improvement_sd",
    "employment_gap_improvement_sd",
    "conversion_shortfall",
    "gap_momentum_state",
    "prob_gap_closing",
    "prob_gap_flat",
    "prob_gap_widening",
    "prob_employment_gap_halves_by_2030",
    "prob_employment_gap_halves_within_10y",
    "median_years_to_half_employment_gap",
    "prob_gap_not_halved_within_15y",
    "development_delay_education_years",
    "development_delay_employment_years",
    "development_delay_joint_years",
    "development_delay_desynchronization_sd_years_years",
    "rural_time_tax_gap_latest_pp",
    "prob_rural_time_tax_gap_shrinking",
    "rural_time_tax_gap_trend",
    "evidence_report_available",
    "evidence_confidence",
    "evidence_mechanism_1",
    "evidence_mechanism_count",
    "complicating_evidence_count",
]
for col in keep:
    if col not in base.columns:
        base[col] = np.nan
wide = base[keep].sort_values("country")
wide.to_csv(OUT / "country_map_layers.csv", index=False)


layers = [
    {
        "id": "education_employment_conversion_gap_z",
        "label": "Education ahead of employment",
        "question": "Where are women’s education outcomes furthest ahead of their employment opportunity?",
        "type": "continuous",
        "unit": "standard deviations",
        "palette": "gold_to_pink_diverging",
        "direction": "Higher means education advantage exceeds employment advantage",
        "source": "Derived from latest gender-specific education and employment composites",
        "recommended": True,
        "caveat": "Different indicators may refer to different years and cohorts; this is not an individual transition measure.",
    },
    {
        "id": "conversion_residual",
        "label": "Opportunity conversion surprise",
        "question": "Which countries perform better or worse on women’s employment opportunity than the model expects?",
        "type": "continuous_signed",
        "unit": "out-of-fold residual SD",
        "palette": "orange_to_blue_diverging",
        "direction": "Negative means under-conversion; positive means above-model conversion",
        "source": "Cross-validated conversion model",
        "recommended": True,
        "caveat": "A residual is a discovery signal, not a causal effect or a ranking of policy quality.",
    },
    {
        "id": "conversion_shortfall",
        "label": "Education progress without employment progress",
        "question": "Where did education gender gaps improve faster than employment gender gaps?",
        "type": "continuous_signed",
        "unit": "difference in improvement SD",
        "palette": "blue_to_orange_diverging",
        "direction": "Higher means a larger conversion shortfall",
        "source": "Endpoint trajectory comparison, 2000–2024 where available",
        "recommended": True,
        "caveat": "Endpoint comparisons are sensitive to coverage years and do not track the same cohort.",
    },
    {
        "id": "desynchronization_sd",
        "label": "Opportunity desynchronization",
        "question": "Where are women’s opportunity dimensions moving at very different levels?",
        "type": "continuous",
        "unit": "within-country SD across observed core domains",
        "palette": "light_to_pink_sequential",
        "direction": "Higher means more uneven outcomes across domains",
        "source": "Education, employment, finance and digital domain composites",
        "recommended": True,
        "caveat": "Compare alongside domain coverage; a country with only a few observed domains can look artificially synchronized.",
    },
    {
        "id": "gap_momentum_state",
        "label": "Gap momentum state",
        "question": "Is the modeled gender opportunity gap closing, flat or widening?",
        "type": "categorical",
        "unit": "state",
        "palette": "closing_flat_widening",
        "direction": "Closing, Flat, or Widening",
        "source": "Hidden Markov state model",
        "recommended": True,
        "caveat": "Show state probabilities in the tooltip; the most likely state can still be uncertain.",
    },
    {
        "id": "prob_gap_widening",
        "label": "Probability the gap is widening",
        "question": "Where is worsening momentum most probable?",
        "type": "probability",
        "unit": "probability",
        "palette": "light_to_orange_sequential",
        "direction": "Higher means stronger modeled evidence of widening",
        "source": "Hidden Markov state model",
        "recommended": True,
        "caveat": "Model probability, not a forecast guarantee.",
    },
    {
        "id": "prob_employment_gap_halves_within_10y",
        "label": "Chance of halving the employment gap within 10 years",
        "question": "Where does the stochastic model indicate faster potential convergence?",
        "type": "probability",
        "unit": "probability",
        "palette": "light_to_blue_sequential",
        "direction": "Higher means greater modeled chance of reaching half the current gap",
        "source": "First-passage simulation",
        "recommended": True,
        "caveat": "Conditional on the fitted historical process; not a policy forecast.",
    },
    {
        "id": "prob_gap_not_halved_within_15y",
        "label": "Risk the employment gap remains sticky",
        "question": "Where is the gap unlikely to halve even within 15 years?",
        "type": "probability",
        "unit": "probability",
        "palette": "light_to_pink_sequential",
        "direction": "Higher means greater modeled persistence",
        "source": "First-passage simulation",
        "recommended": True,
        "caveat": "Conditional on model assumptions and available historical observations.",
    },
    {
        "id": "development_delay_employment_years",
        "label": "Employment development delay",
        "question": "How many reference years separate women’s current employment trajectory from the benchmark trajectory?",
        "type": "continuous",
        "unit": "matched trajectory years",
        "palette": "light_to_gold_sequential",
        "direction": "Higher indicates a longer modeled delay",
        "source": "Development-year matching analysis",
        "recommended": False,
        "caveat": "This is an analogy between trajectories, not a claim that women are literally a fixed number of years behind men.",
    },
    {
        "id": "core_domains_observed",
        "label": "Data visibility",
        "question": "For how many core opportunity domains do we have comparable data?",
        "type": "integer",
        "unit": "domains out of 4",
        "palette": "light_to_blue_sequential",
        "direction": "Higher means better observed coverage",
        "source": "Analysis coverage audit",
        "recommended": True,
        "caveat": "Coverage is not data quality; it only counts observed core domains.",
    },
    {
        "id": "core_year_spread",
        "label": "Asynchronous data years",
        "question": "Where are the latest domain indicators drawn from very different years?",
        "type": "continuous",
        "unit": "years",
        "palette": "light_to_orange_sequential",
        "direction": "Higher means less temporally comparable domain data",
        "source": "Indicator-year audit",
        "recommended": True,
        "caveat": "A large spread can make apparent cross-domain desynchronization partly a timing artifact.",
    },
    {
        "id": "finance_gender_gap_pp",
        "label": "Financial inclusion gender gap",
        "question": "Where is women’s account access furthest below men’s?",
        "type": "continuous_signed",
        "unit": "female minus male percentage points",
        "palette": "orange_to_blue_diverging",
        "direction": "Negative indicates a female disadvantage",
        "source": "World Bank financial inclusion indicators",
        "recommended": True,
        "caveat": "Account ownership does not measure control over money or account usage.",
    },
    {
        "id": "digital_gender_gap_pp",
        "label": "Digital access gender gap",
        "question": "Where is women’s digital access furthest below men’s?",
        "type": "continuous_signed",
        "unit": "female minus male percentage points",
        "palette": "orange_to_blue_diverging",
        "direction": "Negative indicates a female disadvantage",
        "source": "World Bank gender-disaggregated digital indicators",
        "recommended": True,
        "caveat": "Indicator definitions and observation years vary by country.",
    },
    {
        "id": "identity_female_pct",
        "label": "Women with official identification",
        "question": "Where might lack of legal identity constrain access to work, finance and services?",
        "type": "percentage",
        "unit": "percent of women",
        "palette": "light_to_blue_sequential",
        "direction": "Higher means more women report official ID ownership",
        "source": "World Bank ID4D",
        "recommended": True,
        "caveat": "Coverage is sparse and ID ownership does not guarantee usable or safe digital identity.",
    },
    {
        "id": "time_tax_extra_hours_day",
        "label": "Women’s unpaid-care time tax",
        "question": "Where do women spend the most additional hours per day on unpaid work relative to men?",
        "type": "continuous_signed",
        "unit": "female minus male hours per day",
        "palette": "light_to_pink_sequential",
        "direction": "Higher means a larger female time burden",
        "source": "Gender-disaggregated time-use indicators",
        "recommended": True,
        "caveat": "Time-use data are sparse and survey instruments are not perfectly harmonized.",
    },
    {
        "id": "rural_time_tax_gap_latest_pp",
        "label": "Rural time-tax infrastructure gap",
        "question": "Where do rural households face the largest infrastructure access gap relevant to women’s time poverty?",
        "type": "continuous",
        "unit": "composite gap points",
        "palette": "light_to_gold_sequential",
        "direction": "Higher means a larger rural disadvantage",
        "source": "Rural–urban infrastructure gap analysis",
        "recommended": True,
        "caveat": "This is a contextual household infrastructure measure, not an individual women-only outcome.",
    },
    {
        "id": "maternal_mortality_ratio",
        "label": "Maternal mortality",
        "question": "Where do severe maternal-health risks remain highest?",
        "type": "continuous",
        "unit": "deaths per 100,000 live births",
        "palette": "light_to_pink_sequential",
        "direction": "Higher means worse maternal-health outcomes",
        "source": "World Bank health indicators",
        "recommended": False,
        "caveat": "Use a log scale for the legend because the cross-country distribution is strongly skewed.",
    },
    {
        "id": "evidence_report_available",
        "label": "Human-reviewed evidence coverage",
        "question": "Which statistical anomalies already have a structured supporting-and-contradicting evidence review?",
        "type": "boolean",
        "unit": "review available",
        "palette": "neutral_to_blue",
        "direction": "True means a reviewed pilot report is available",
        "source": "Conversion Evidence Agent pilot",
        "recommended": True,
        "caveat": "Evidence availability is not evidence that a proposed mechanism is causal.",
    },
]

catalog = pd.DataFrame(layers)
catalog.to_csv(OUT / "layer_catalog.csv", index=False)
(OUT / "layer_catalog.json").write_text(json.dumps(layers, ensure_ascii=False, indent=2) + "\n")


long_rows = []
for layer in layers:
    col = layer["id"]
    if col not in wide.columns:
        continue
    for _, row in wide[["iso3", "country", col]].iterrows():
        if pd.isna(row[col]):
            continue
        value = row[col]
        if isinstance(value, (np.bool_, bool)):
            value = bool(value)
        elif isinstance(value, (np.integer, int)):
            value = int(value)
        elif isinstance(value, (np.floating, float)):
            value = float(value)
        long_rows.append(
            {
                "iso3": row["iso3"],
                "country": row["country"],
                "layer_id": col,
                "layer_label": layer["label"],
                "value": value,
                "unit": layer["unit"],
            }
        )
pd.DataFrame(long_rows).to_csv(OUT / "map_layers_long.csv", index=False)


cards = []
for _, row in wide.iterrows():
    cards.append(
        {
            "iso3": row["iso3"],
            "country": row["country"],
            "headline": {
                "conversion_residual": None if pd.isna(row["conversion_residual"]) else round(float(row["conversion_residual"]), 3),
                "education_ahead_of_employment_z": None if pd.isna(row["education_employment_conversion_gap_z"]) else round(float(row["education_employment_conversion_gap_z"]), 3),
                "momentum_state": None if pd.isna(row["gap_momentum_state"]) else row["gap_momentum_state"],
                "probability_widening": None if pd.isna(row["prob_gap_widening"]) else round(float(row["prob_gap_widening"]), 3),
            },
            "coverage": {
                "core_domains_observed": None if pd.isna(row["core_domains_observed"]) else int(row["core_domains_observed"]),
                "latest_core_observation_year": None if pd.isna(row["latest_core_observation_year"]) else int(row["latest_core_observation_year"]),
                "core_year_spread": None if pd.isna(row["core_year_spread"]) else int(row["core_year_spread"]),
            },
            "evidence": {
                "available": bool(row["evidence_report_available"]),
                "confidence": None if pd.isna(row["evidence_confidence"]) else row["evidence_confidence"],
                "leading_mechanism": None if pd.isna(row["evidence_mechanism_1"]) else row["evidence_mechanism_1"],
                "complicating_evidence_count": None if pd.isna(row["complicating_evidence_count"]) else int(row["complicating_evidence_count"]),
            },
        }
    )
(OUT / "country_detail_cards.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n")


recommended = [layer for layer in layers if layer["recommended"]]
audit = {
    "countries": int(len(wide)),
    "layers": len(layers),
    "recommended_layers": len(recommended),
    "long_rows": len(long_rows),
    "pilot_evidence_countries": int(wide["evidence_report_available"].sum()),
    "coverage_by_layer": {
        layer["id"]: int(wide[layer["id"]].notna().sum())
        for layer in layers
        if layer["id"] in wide.columns
    },
}
(OUT / "pack_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")


blueprint = """# Map visualization blueprint

The pack contains continuous, categorical, probability and evidence-coverage layers that can be joined to world geometry using `iso3`.

## Recommended story sequence

1. **Education ahead of employment** — establish the core research tension without declaring a threshold-based stage.
2. **Opportunity conversion surprise** — reveal countries that are above or below a cross-validated expectation.
3. **Gap momentum state** — distinguish a currently large gap from one that is closing, flat or widening.
4. **Sticky-gap probability** — add the stochastic first-passage view without calling it a deterministic forecast.
5. **Care, finance, digital and identity layers** — let users inspect plausible bottlenecks separately.
6. **Data visibility and asynchronous years** — make missingness and temporal mismatch visible rather than hiding uncertainty.
7. **Evidence coverage** — open structured supporting and contradicting evidence for reviewed countries.

## Country tooltip

The default tooltip should show country, selected value and unit, observation/model year when available, core-domain coverage, and one concise caveat. Do not show a bare score without the period and coverage.

## Country detail panel

Use a compact profile rather than one overall rank:

- education gap;
- employment gap;
- finance gap;
- digital gap;
- unpaid-care time tax;
- conversion residual;
- closing/flat/widening probabilities;
- first-passage probability;
- data coverage and year spread;
- evidence mechanism, contradiction count and confidence when a report exists.

## Visual rules

- Use a centered diverging scale for signed gender gaps and residuals.
- Use a sequential scale for probabilities and burdens.
- Keep missing countries light gray and clickable, with a “data unavailable” explanation.
- Do not discretize continuous layers into arbitrary stages unless the interface explicitly labels the cutoffs and offers sensitivity checks.
- For HMM states, show all three probabilities in the tooltip; color only the most likely state.
- For first-passage results, use “modeled probability” and “conditional on historical dynamics,” never “will converge.”
- The development-delay layer is optional and must use the phrase “trajectory resemblance,” not “women are literally N years behind.”
"""
(OUT / "visualization_blueprint.md").write_text(blueprint)

print(json.dumps(audit, indent=2))
