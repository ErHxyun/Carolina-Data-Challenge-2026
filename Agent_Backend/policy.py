"""Deterministic planning intent and target arithmetic; never a policy forecast."""
import re
import math
from datetime import date


def planning_intent(question):
    text = question.casefold()
    mode = bool(re.search(r"roadmap|policy|address.*gap|close.*gap|halve|reduce.*gap|政策|路线图|缩小|减半|消除.*差距", text))
    result = {"output_mode": "policy_roadmap" if mode else "research_brief"}
    if not mode:
        return result
    years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", text)
    target = re.search(r"(?:by|到|截至)\s*((?:19|20)\d{2})", text)
    result["target_year"] = int(target[1]) if target else int(years[-1]) if years else None
    reduction = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    result["reduction_pct"] = float(reduction[1]) if reduction else 50 if re.search(r"halve|减半", text) else 100 if re.search(r"close.*gap|eliminate.*gap|消除.*差距", text) else None
    return result


def validate_planning(route):
    intent = planning_intent(str(route.get("question", "")))
    mode = route.get("output_mode", intent["output_mode"])
    if mode not in ("research_brief", "policy_roadmap"):
        raise ValueError("Unsupported report mode")
    year = route.get("target_year", intent.get("target_year"))
    reduction = route.get("reduction_pct", intent.get("reduction_pct"))
    if year is not None and (type(year) is not int or not 1900 <= year <= 2100):
        raise ValueError("Target year must be between 1900 and 2100")
    if reduction is not None and (type(reduction) not in (int, float) or not math.isfinite(reduction) or not 0 <= reduction <= 100):
        raise ValueError("Gap reduction must be between 0 and 100 percent")
    return {"output_mode": mode, "target_year": year, "reduction_pct": reduction}


def target_scenario(route, bundle, current_year=None):
    current_year = current_year or date.today().year
    result = {"status": "qualitative", "planning_year": current_year,
              "target_year": route.get("target_year"), "reduction_pct": route.get("reduction_pct"),
              "baseline_year": None, "baseline": None, "target": None,
              "annual_change": None, "unit": None, "evidence_ids": [],
              "warnings": ["Illustrative target path, not a forecast or an estimated policy effect. Monitor both groups; do not narrow a gap by worsening outcomes for the advantaged group."]}
    if result["target_year"] is not None and result["target_year"] <= current_year:
        result["status"] = "retrospective"
        result["warnings"].append("Review this historical target retrospectively, not as a future implementation deadline.")
    candidates = []
    for fact in bundle["facts"]:
        for row in fact["rows"]:
            if row.get("cross_source_conflict") or row.get("either_endpoint_flagged"):
                continue
            value = None
            year = row.get("year", row.get("year_end"))
            if route["topic"] in ("time_tax", "time_changes", "freed_time"):
                value = row.get("time_gap_hours", row.get("time_gap_hours_end"))
                unit = "female-minus-male unpaid hours/day"
            elif route["topic"] == "opportunity_gap" and fact["id"] == "opportunity-model":
                rural, urban = row.get("rural", {}).get("median"), row.get("urban", {}).get("median")
                value = abs(urban-rural) if rural is not None and urban is not None else None
                unit = "absolute modeled rural–urban opportunity gap (latent units)"
            elif route["topic"] == "infrastructure" and fact["id"] == "local-analysis":
                text = route.get("question", "").casefold()
                selected = [key for word, key in [("water", "water_gap"), ("electricity", "electricity_gap"), ("cooking", "cooking_gap")] if word in text]
                if len(selected) == 1 and row.get(selected[0]) is not None:
                    value = row[selected[0]] * 100
                unit = "national access shortfall (percentage points), not a gender gap"
            else:
                continue
            if type(value) in (int, float) and math.isfinite(value) and value >= 0 and year is not None:
                candidates.append((int(year), value, unit, fact["id"]))
    if not candidates:
        result["warnings"].append("No unambiguous eligible gap baseline. Use a qualitative roadmap; infrastructure indices and opportunity delay are not policy forecasts.")
        return result
    latest = max(c[0] for c in candidates)
    eligible = [c for c in candidates if c[0] == latest]
    if len({c[1] for c in eligible}) > 1:
        result["warnings"].append("Conflicting latest baselines require review before target calculation.")
        return result
    year, baseline, unit, evidence = eligible[0]
    result.update(baseline_year=year, baseline=baseline, unit=unit, evidence_ids=[evidence])
    if year < current_year:
        result["warnings"].append(f"Baseline is from {year}, not {current_year}. Refresh measurement before committing resources; the annual rate spans the historical baseline to the target.")
    target_year, reduction = result["target_year"], result["reduction_pct"]
    if target_year is not None and target_year <= current_year:
        result["status"] = "retrospective"
        result["warnings"].append("Target date has passed or is the current year; assess retrospectively, not as a future implementation plan.")
        return result
    if target_year is None or reduction is None or target_year <= year:
        result["warnings"].append("Specify a future target year and percentage gap reduction for a numeric target path.")
        return result
    target = baseline * (1 - reduction/100)
    result.update(status="illustrative", target=target, annual_change=(target-baseline)/(target_year-year))
    return result


ROADMAP_PROMPT = """
Write a policy roadmap in JSON {"sections":[{"title":"...","text":"...","evidence_ids":["..."]}]}.
Use 4-6 concise sections: baseline and target, up to THREE priority actions, implementation and monitoring.
The supplied scenario is deterministic and authoritative: never invent or recalculate a baseline, target, budget, effect size, completion date, or probability of success.
If qualitative, explain missing inputs and propose measurement before targets. If retrospective, discuss review of past implementation rather than future steps toward a past date.
For each action name a proposed responsible actor, concrete steps, dependencies, monitoring indicator and evidence scope (country-specific, transferable from elsewhere, or proposal requiring validation).
Distinguish documented policy from your proposed action. Evidence citations support context, not proof the target can be achieved.
Use near-term measurement/pilot, medium-term evaluation, and conditional scale-up phases only for future targets.
Monitor women's absolute unpaid hours and service access alongside gaps. Do not claim parity through deterioration of the better-off group.
Only cite supplied evidence IDs. No URLs in prose. No causal conclusions from correlations. When web retrieval is unavailable, explicitly limit recommendations to provisional research priorities.
"""
