from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "outputs" / "opportunity_synchronization" / "country_opportunity_profiles.csv"
PANEL = ROOT / "outputs" / "opportunity_gap_model" / "country_year_opportunity_gap_panel.csv.gz"
OUT = ROOT / "outputs" / "conversion_evidence_agent"
OUT.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "education_advantage_raw",
    "finance_advantage_raw",
    "digital_advantage_raw",
    "log_gdp_per_capita_ppp",
    "government_effectiveness",
    "rural_population_pct",
    "fertility_rate",
]


REPORT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Conversion Evidence Report",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "task_id", "country", "statistical_signal", "mechanisms",
        "contradicting_or_complicating_evidence", "overall_confidence",
        "causal_conclusion", "limitations", "search_summary",
    ],
    "properties": {
        "task_id": {"type": "string"},
        "country": {"type": "object", "required": ["iso3", "name"], "properties": {
            "iso3": {"type": "string"}, "name": {"type": "string"}}, "additionalProperties": False},
        "statistical_signal": {"type": "object", "required": ["statement", "period", "uncertainty_note"], "properties": {
            "statement": {"type": "string"}, "period": {"type": "string"},
            "uncertainty_note": {"type": "string"}}, "additionalProperties": False},
        "mechanisms": {"type": "array", "maxItems": 3, "items": {"type": "object", "additionalProperties": False,
            "required": ["mechanism", "supporting_evidence", "confidence", "confidence_reason"],
            "properties": {
                "mechanism": {"type": "string"},
                "supporting_evidence": {"type": "array", "items": {"$ref": "#/$defs/evidence"}},
                "confidence": {"enum": ["high", "medium", "low", "insufficient"]},
                "confidence_reason": {"type": "string"}}}},
        "contradicting_or_complicating_evidence": {"type": "array", "items": {"$ref": "#/$defs/evidence"}},
        "overall_confidence": {"enum": ["high", "medium", "low", "insufficient"]},
        "causal_conclusion": {"const": False},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "search_summary": {"type": "object", "required": ["sources_searched", "no_evidence_found_for"], "properties": {
            "sources_searched": {"type": "array", "items": {"type": "string"}},
            "no_evidence_found_for": {"type": "array", "items": {"type": "string"}}}, "additionalProperties": False},
    },
    "$defs": {"evidence": {"type": "object", "additionalProperties": False,
        "required": ["claim", "organization", "title", "publication_year", "url", "relevance", "time_match"],
        "properties": {
            "claim": {"type": "string"}, "organization": {"type": "string"},
            "title": {"type": "string"}, "publication_year": {"type": ["integer", "null"]},
            "url": {"type": "string", "format": "uri"}, "relevance": {"type": "string"},
            "time_match": {"enum": ["before", "during", "after", "unclear"]}}}},
}


def latest_predictors(panel: pd.DataFrame) -> pd.DataFrame:
    fields = ["log_gdp_per_capita_ppp", "government_effectiveness", "rural_population_pct", "fertility_rate"]
    pieces = []
    for field in fields:
        g = panel.dropna(subset=[field]).sort_values(["iso3", "year"]).groupby("iso3", as_index=False).tail(1)
        pieces.append(g[["iso3", field, "year"]].rename(columns={"year": f"{field}_year"}))
    out = pieces[0]
    for p in pieces[1:]:
        out = out.merge(p, on="iso3", how="outer")
    return out


def fit_cross_section() -> pd.DataFrame:
    profile = pd.read_csv(PROFILE)
    panel = pd.read_csv(PANEL)
    frame = profile.merge(latest_predictors(panel), on="iso3", how="left")
    data = frame.dropna(subset=["employment_advantage_raw", "education_advantage_raw"]).copy()

    model = Pipeline([
        ("prep", ColumnTransformer([("num", Pipeline([
            ("imp", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]), FEATURES)])),
        ("model", ElasticNet(alpha=0.05, l1_ratio=0.2, max_iter=20000)),
    ])
    cv = KFold(n_splits=10, shuffle=True, random_state=20260926)
    data["expected_employment_advantage"] = cross_val_predict(model, data[FEATURES], data["employment_advantage_raw"], cv=cv)
    data["conversion_residual"] = data["employment_advantage_raw"] - data["expected_employment_advantage"]
    data["residual_percentile"] = data["conversion_residual"].rank(pct=True)
    return data


def improvement_divergence(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for iso3, g in panel.groupby("iso3"):
        g = g.sort_values("year")
        edu = g.dropna(subset=["education_gap"])
        emp = g.dropna(subset=["employment_gap"])
        if len(edu) < 6 or len(emp) < 10:
            continue
        e0, e1 = edu.iloc[0], edu.iloc[-1]
        m0, m1 = emp.iloc[0], emp.iloc[-1]
        edu_improvement = float(e0["education_gap"] - e1["education_gap"])
        emp_improvement = float(m0["employment_gap"] - m1["employment_gap"])
        rows.append({
            "iso3": iso3, "country": g.iloc[-1]["country"],
            "education_start_year": int(e0["year"]), "education_end_year": int(e1["year"]),
            "employment_start_year": int(m0["year"]), "employment_end_year": int(m1["year"]),
            "education_gap_improvement_sd": edu_improvement,
            "employment_gap_improvement_sd": emp_improvement,
            "conversion_shortfall": edu_improvement - emp_improvement,
        })
    return pd.DataFrame(rows)


def prompt_for(row: pd.Series, kind: str, task_id: str) -> dict:
    if kind == "persistent_under_conversion":
        signal = (
            f"{row.country}'s latest female employment-opportunity score is {row.employment_advantage_raw:.2f} SD relative to men. "
            f"A cross-validated model using education, financial inclusion, digital inclusion and macro conditions expected {row.expected_employment_advantage:.2f} SD. "
            f"The out-of-fold residual is {row.conversion_residual:.2f} SD (lower {row.residual_percentile:.0%} of countries), indicating under-conversion relative to comparable observations."
        )
        period = "Latest available observations through 2024"
    elif kind == "positive_converter":
        upper_tail = max(0.01, 1 - float(row.residual_percentile))
        signal = (
            f"{row.country}'s latest female employment-opportunity score is {row.employment_advantage_raw:.2f} SD relative to men, compared with an out-of-fold expected value of "
            f"{row.expected_employment_advantage:.2f} SD. The positive residual is {row.conversion_residual:.2f} SD (approximately the upper {upper_tail:.0%} tail), suggesting stronger conversion than comparable observations."
        )
        period = "Latest available observations through 2024"
    else:
        signal = (
            f"Between {int(row.education_start_year)} and {int(row.education_end_year)}, {row.country}'s education gender gap improved by {row.education_gap_improvement_sd:.2f} SD, while its employment gender gap improved by only "
            f"{row.employment_gap_improvement_sd:.2f} SD between {int(row.employment_start_year)} and {int(row.employment_end_year)}. The descriptive conversion shortfall is {row.conversion_shortfall:.2f} SD."
        )
        period = f"{int(min(row.education_start_year, row.employment_start_year))}-{int(max(row.education_end_year, row.employment_end_year))}"

    prompt = f"""You are an evidence-retrieval agent supporting a cross-country statistical study of when women's educational progress does or does not translate into employment opportunity.

STATISTICAL SIGNAL
{signal}

This signal is descriptive and model-dependent. It is not proof of a policy mechanism or causal effect.

TASK
Search authoritative primary or institutional sources for documented policies, structural constraints, programmes or shocks in {row.country} during or immediately before {period} that could plausibly help contextualize this signal. Prioritize World Bank, ILO, UN Women, national statistics offices, government legislation, OECD where applicable, and peer-reviewed research.

Focus on mechanisms connecting education to employment: childcare and unpaid care, labor regulation, occupational segregation, transport and safety, digital and financial inclusion, legal identity, marriage/family law, public-sector employment, conflict, migration and macroeconomic shocks.

REQUIREMENTS
1. Find supporting evidence and actively search for contradicting or complicating evidence.
2. Every factual evidence item must include an accessible URL, organization, title and publication year.
3. Distinguish publication date from the period described by the source.
4. Do not claim causality. Do not imply that temporal coincidence proves explanation.
5. If authoritative evidence is absent, record that explicitly rather than filling the gap with speculation.
6. Return JSON conforming exactly to the supplied Conversion Evidence Report schema, with task_id={task_id!r} and causal_conclusion=false.
"""
    return {"task_id": task_id, "kind": kind, "iso": row.iso3, "country": row.country,
            "period": period, "statistical_signal": signal, "prompt": prompt}


def main() -> None:
    cross = fit_cross_section()
    panel = pd.read_csv(PANEL)
    divergence = improvement_divergence(panel)

    tasks = []
    under = cross.nsmallest(15, "conversion_residual")
    positive = cross.nlargest(10, "conversion_residual")
    diverging = divergence[divergence["education_gap_improvement_sd"] > 0].nlargest(10, "conversion_shortfall")
    for i, (_, r) in enumerate(under.iterrows(), 1):
        tasks.append(prompt_for(r, "persistent_under_conversion", f"CONV-U-{i:03d}"))
    for i, (_, r) in enumerate(positive.iterrows(), 1):
        tasks.append(prompt_for(r, "positive_converter", f"CONV-P-{i:03d}"))
    for i, (_, r) in enumerate(diverging.iterrows(), 1):
        tasks.append(prompt_for(r, "education_progress_without_employment_conversion", f"CONV-D-{i:03d}"))

    with open(OUT / "conversion_evidence_prompts.jsonl", "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    (OUT / "conversion_evidence_report_schema.json").write_text(json.dumps(REPORT_SCHEMA, indent=2), encoding="utf-8")
    cross.to_csv(OUT / "conversion_residual_candidates.csv", index=False)
    divergence.to_csv(OUT / "education_employment_divergence_candidates.csv", index=False)

    audit = {
        "legacy_prompt_count": 201,
        "new_task_count": len(tasks),
        "new_task_counts": pd.Series([t["kind"] for t in tasks]).value_counts().to_dict(),
        "important_limitations": [
            "The cross-sectional residual model is exploratory and does not identify causal mechanisms.",
            "Out-of-fold residuals reduce in-sample optimism but are not confidence intervals.",
            "Sparse finance and digital observations mix survey years and must be shown with their dates.",
            "The education-progress divergence statistic compares endpoints and is sensitive to available-year coverage.",
            "Prompts are investigation tasks, not completed evidence reports.",
        ],
    }
    (OUT / "task_generation_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
