"""
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
