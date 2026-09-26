"""
Predictive v2 — Step 3a: how strongly is each predictor associated with gap-closing velocity v?
- All predictors z-scored -> coefficients comparable (effect of +1 SD).
- v reported in milli-SD per year (x1000).
- Model B ("between+within"): pooled OLS + region & year FE      -> do countries with more X close faster?
- Model W ("within"):         country FE + year FE (two-way)     -> when X rises inside a country, does v rise?
- SE clustered by country (overlapping windows are autocorrelated).
- Group importance: drop one variable group at a time, loss in R2 (B) / within-R2 (W).
Horizons: 3 and 5 years. Associational, not causal.
"""
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
import warnings; warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "predictive_v2"
P = pd.read_csv(OUT / "panel_v2.csv.gz").sort_values(["iso3", "year"])
# add 5-year target from the raw gap series
full = P.set_index(["iso3", "year"])["gap_employment"]
for h in (3, 5):
    fut = P[["iso3", "year", "gap_employment"]].copy(); fut["year"] -= h
    P = P.merge(fut.rename(columns={"gap_employment": f"_g{h}"}), on=["iso3", "year"], how="left")
    P[f"v{h}"] = -(P[f"_g{h}"] - P["gap_employment"]) / h * 1000

GROUPS = {
    "momentum/state": ["gap_employment_tr", "v_employment_past3"],
    "time tax / infrastructure": ["clean_cooking", "basic_water_rural", "electricity_rural", "d3_clean_cooking", "d3_electricity_rural"],
    "structure": ["fertility", "d3_fertility", "fem_agri_emp_share", "d3_fem_agri_emp_share", "urban_share", "urban_growth", "log_gdppc_ppp"],
    "shocks": ["gdppc_growth_3y", "recession_last3y"],
    "edu-emp misalignment": ["edu_emp_misalign"],
}
LABEL = {"gap_employment_tr": "Current employment gap", "v_employment_past3": "Past 3-yr velocity",
         "clean_cooking": "Clean cooking access", "basic_water_rural": "Rural basic water", "electricity_rural": "Rural electricity",
         "d3_clean_cooking": "Δ clean cooking", "d3_electricity_rural": "Δ rural electricity",
         "fertility": "Fertility rate", "d3_fertility": "Δ fertility", "fem_agri_emp_share": "Women in agriculture (share)",
         "d3_fem_agri_emp_share": "Δ women in agriculture", "urban_share": "Urban share", "urban_growth": "Urban growth",
         "log_gdppc_ppp": "log GDP per capita", "gdppc_growth_3y": "GDP pc growth (3y)", "recession_last3y": "Recession in last 3y",
         "edu_emp_misalign": "Edu–employment misalignment"}
X_ALL = [v for g in GROUPS.values() for v in g]

def prep(h, cols):
    d = P.dropna(subset=[f"v{h}"] + cols).copy()
    for c in cols: d[c] = (d[c] - d[c].mean()) / d[c].std()
    return d

def fit(d, cols, h, within):
    y = d[f"v{h}"]; X = d[cols].copy()
    if within:   # two-way FE by demeaning country, then year dummies
        yd = y - d.groupby("iso3")[f"v{h}"].transform("mean")
        Xd = X - X.groupby(d["iso3"]).transform("mean")
        yrs = pd.get_dummies(d["year"], prefix="y", drop_first=True, dtype=float)
        yrs = yrs - yrs.groupby(d["iso3"]).transform("mean")
        M = pd.concat([Xd, yrs], axis=1); yy = yd
    else:
        dummies = pd.get_dummies(d[["region_name"]].fillna("NA").assign(year=d.year.astype(str)), drop_first=True, dtype=float)
        M = sm.add_constant(pd.concat([X, dummies], axis=1)); yy = y
    r = sm.OLS(yy, M).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d["iso3"])[0]})
    return r

rows, imp = [], []
for h in (3, 5):
    for spec, cols in [("core", [c for c in X_ALL if c != "edu_emp_misalign"]), ("with_misalign", X_ALL)]:
        d = prep(h, cols)
        for within in (False, True):
            r = fit(d, cols, h, within); model = "W: within-country" if within else "B: between+within"
            ci = r.conf_int()
            for c in cols:
                rows.append(dict(horizon=h, spec=spec, model=model, predictor=c, label=LABEL[c],
                                 group=[g for g, v in GROUPS.items() if c in v][0],
                                 coef=r.params[c], lo=ci.loc[c, 0], hi=ci.loc[c, 1], p=r.pvalues[c],
                                 n=int(r.nobs), countries=d.iso3.nunique(), r2=r.rsquared, sd_y=d[f"v{h}"].std()))
            base = r.rsquared
            for g, gv in GROUPS.items():
                keep = [c for c in cols if c not in gv]
                if len(keep) == len(cols): continue
                imp.append(dict(horizon=h, spec=spec, model=model, group=g, r2_full=base,
                                r2_drop=base - fit(d, keep, h, within).rsquared))
C = pd.DataFrame(rows); I = pd.DataFrame(imp)
C.to_csv(OUT / "predictor_effects.csv", index=False); I.to_csv(OUT / "group_importance.csv", index=False)
pd.set_option("display.width", 220)
for h in (3, 5):
    t = C[(C.horizon == h) & (C.spec == "core")].pivot_table(index="label", columns="model", values=["coef", "p"]).round(3)
    print(f"\n=== horizon {h}y, core spec: coef = change in v (milli-SD/yr) per +1 SD of predictor ===")
    print(t.sort_values(("coef", "B: between+within")).to_string())
    print(C[(C.horizon == h) & (C.spec == "core")].groupby("model")[["n", "countries", "r2", "sd_y"]].first().round(3).to_string())
print("\n=== group importance (R2 lost when group dropped) ===")
print(I.pivot_table(index=["group"], columns=["horizon", "spec", "model"], values="r2_drop").round(3).to_string())
