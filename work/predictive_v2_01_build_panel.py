"""
Predictive model v2 — Step 2: build the modeling panel.
Target (decided with Gloria, 2026-09-26): gap-closing velocity
    G_t   = Z^M_t - Z^F_t            (gap in pooled-SD score units, per domain)
    v_t   = -(G_{t+3} - G_t) / 3      (SD units closed per year over the next 3 years; >0 = catching up)
Features use ONLY information available at year t (trailing windows; no centered smoothing).
Outputs -> outputs/predictive_v2/
"""
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "predictive_v2"; OUT.mkdir(exist_ok=True)
SC = ROOT / "outputs" / "development_wait_analysis" / "opportunity_scores.csv.gz"
CMB = ROOT / "outputs" / "world_bank_sources" / "combined"
META = ROOT / "outputs" / "world_bank_indicators_wide_2010_2024.csv"
H = 3

# ---------- target & state features from opportunity scores ----------
s = pd.read_csv(SC)
w = s.pivot_table(index=["iso3", "year"], columns="sex", values=["education_score", "employment_score"])
w.columns = [f"{a.split('_')[0]}_{b[0]}" for a, b in w.columns]      # education_f, employment_m, ...
w = w.reset_index().sort_values(["iso3", "year"])
full = pd.MultiIndex.from_product([w.iso3.unique(), range(2000, 2025)], names=["iso3", "year"])
w = w.set_index(["iso3", "year"]).reindex(full).reset_index()
g = w.groupby("iso3")
for d in ["education", "employment"]:
    w[f"gap_{d}"] = w[f"{d}_m"] - w[f"{d}_f"]
    # trailing 3-year mean (information available at t)
    w[f"gap_{d}_tr"] = g[f"gap_{d}"].transform(lambda x: x.rolling(3, min_periods=2).mean())
    w[f"fem_{d}_tr"] = g[f"{d}_f"].transform(lambda x: x.rolling(3, min_periods=2).mean())
    w[f"v_{d}_past3"] = -(w[f"gap_{d}"] - g[f"gap_{d}"].shift(3)) / 3
    # TARGET: future velocity
    w[f"target_v_{d}"] = -(g[f"gap_{d}"].shift(-H) - w[f"gap_{d}"]) / H
w["edu_emp_misalign"] = w["gap_employment_tr"] - w["gap_education_tr"]   # >0: employment gap larger than education gap

# ---------- external predictors ----------
PRED = {  # code: (name, source, transform)
    "EG.CFT.ACCS.ZS": ("clean_cooking", "002_WDI"),
    "EG.CFT.ACCS.RU.ZS": ("clean_cooking_rural", "002_WDI"),
    "SH.H2O.BASW.ZS": ("basic_water", "016_HNP"),
    "SH.H2O.BASW.RU.ZS": ("basic_water_rural", "016_HNP"),
    "EG.ELC.ACCS.RU.ZS": ("electricity_rural", "002_WDI"),
    "SP.DYN.TFRT.IN": ("fertility", "002_WDI"),
    "SL.AGR.EMPL.FE.ZS": ("fem_agri_emp_share", "002_WDI"),
    "SP.URB.GROW": ("urban_growth", "002_WDI"),
    "SP.URB.TOTL.IN.ZS": ("urban_share", "002_WDI"),
    "NY.GDP.PCAP.KD.ZG": ("gdppc_growth", "002_WDI"),
    "NY.GDP.PCAP.PP.KD": ("gdppc_ppp", "002_WDI"),
    "IQ.SPI.OVRL": ("stat_performance", "002_WDI"),
}
frames = []
for src in sorted({v[1] for v in PRED.values()}):
    codes = [c for c, v in PRED.items() if v[1] == src]
    x = pd.read_parquet(CMB / f"{src}_wide.parquet", columns=["iso3", "year", "is_aggregate"] + codes)
    frames.append(x[~x.is_aggregate].drop(columns="is_aggregate").set_index(["iso3", "year"]).rename(columns={c: PRED[c][0] for c in codes}))
X = pd.concat(frames, axis=1).reset_index()
X = X[X.year.between(1995, 2024)].sort_values(["iso3", "year"])
gx = X.groupby("iso3")
# carry forward sparse/slow series at most 3 years (information available at t), never backward
for c in ["clean_cooking", "clean_cooking_rural", "basic_water", "basic_water_rural", "electricity_rural", "fem_agri_emp_share", "stat_performance"]:
    X[c] = gx[c].ffill(limit=3)
X["log_gdppc_ppp"] = np.log(X.pop("gdppc_ppp"))
for c in ["clean_cooking", "basic_water_rural", "electricity_rural", "fertility", "fem_agri_emp_share", "urban_share"]:
    X[f"d3_{c}"] = (X[c] - gx[c].shift(3)) / 3           # trailing 3-yr change per year
X["gdppc_growth_3y"] = gx["gdppc_growth"].transform(lambda x: x.rolling(3, min_periods=2).mean())
X["recession_last3y"] = gx["gdppc_growth"].transform(lambda x: (x < 0).astype(float).where(x.notna()).rolling(3, min_periods=1).max())
X = X.drop(columns=["gdppc_growth"])

P = w.merge(X, on=["iso3", "year"], how="left")
meta = pd.read_csv(META, usecols=["country_code", "country_name", "region_name", "income_level_name"]).drop_duplicates("country_code")
P = P.merge(meta.rename(columns={"country_code": "iso3"}), on="iso3", how="left")
P["target_year"] = P.year + H
P = P[P.year.between(2003, 2024)]
P.to_csv(OUT / "panel_v2.csv.gz", index=False)

# ---------- descriptives ----------
lines = []
for d in ["employment", "education"]:
    t = P.dropna(subset=[f"target_v_{d}"])
    y = t[f"target_v_{d}"]
    ac = t[[f"target_v_{d}", f"v_{d}_past3"]].dropna().corr().iloc[0, 1]
    lines.append(dict(domain=d, rows=len(t), countries=t.iso3.nunique(), years=f"{t.year.min()}-{t.year.max()}",
                      mean_v=y.mean(), median_v=y.median(), sd_v=y.std(), share_closing=(y > 0).mean(),
                      share_widening=(y < 0).mean(), corr_with_past_v=ac,
                      median_gap_now=t[f"gap_{d}_tr"].median()))
D = pd.DataFrame(lines).round(3); D.to_csv(OUT / "target_descriptives.csv", index=False)
feat = [c for c in P.columns if c not in ["iso3", "year", "country_name", "region_name", "income_level_name", "target_year"]
        and not c.startswith("target_") and not c.endswith(("_f", "_m")) and c not in ("gap_education", "gap_employment")]
cov = P.dropna(subset=["target_v_employment"])[feat].notna().mean().sort_values().round(3)
cov.rename("coverage_in_employment_target_rows").to_csv(OUT / "feature_coverage.csv")
print(D.to_string(index=False)); print(cov.to_string())
