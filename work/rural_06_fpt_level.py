"""
Framework item 1 (fixed threshold): when does the RURAL level reach TODAY's URBAN level?
    T*_c = inf{h >= 0 : Z^rural_{c,2024+h} >= Z*_c},   Z*_c = urban latent level in 2024 (drawn from its filtered distribution)
Series: clean cooking, basic water, basic sanitation, electricity, infrastructure composite (annual, % of population),
        women's non-farm employment share (JOIN, survey years).
Model: local level + drift (Kalman), drift pooled within region (EB); drift uncertainty floor calibrated on a
2014 -> 2023 backtest of rural levels (half of countries calibrate, the other half validates).
Reports P(T* <= 2030 | data), P(T* <= 2050), median T*, 'unlikely before 2100' when P(T* <= 2100) < 0.5.
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from multiprocessing import Pool
from statsmodels.tsa.statespace.structural import UnobservedComponents
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"
P = pd.read_csv(OUT / "rural_urban_panel.csv.gz")
for c in ["fem_nonag_rural", "fem_nonag_urban"]: P[c] = P[c] * 100
S = {"cooking": ("cooking_rural", "cooking_urban"), "water": ("water_rural", "water_urban"), "sanitation": ("sanitation_rural", "sanitation_urban"),
     "electricity": ("electricity_rural", "electricity_urban"), "infra": ("infra_rural", "infra_urban"), "jobs": ("fem_nonag_rural", "fem_nonag_urban")}
reg = P.drop_duplicates("iso3").set_index("iso3")[["country_name", "region_name", "income_level_name"]]
rng = np.random.default_rng(5)

def fit(args):
    key, col, iso, years, vals, end = args
    y = pd.Series(vals, index=years).reindex(range(2000, end + 1))
    sparse = key == "jobs"
    if y.notna().sum() < (4 if sparse else 8) or y.last_valid_index() < end - (8 if sparse else 3): return None
    try: r = UnobservedComponents(y.values, level="lldtrend").fit(disp=False, maxiter=200)
    except Exception: return None
    nm = list(r.model.param_names)
    return dict(key=key, col=col, iso3=iso, end=end, a0=r.filtered_state[0, -1], a1=r.filtered_state[1, -1], P00=r.filtered_state_cov[0, 0, -1],
                P01=r.filtered_state_cov[0, 1, -1], P11=r.filtered_state_cov[1, 1, -1], sl=np.sqrt(max(r.params[nm.index("sigma2.level")], 0)))

def run_fits(end):
    D = P[P.year.between(2000, end)]
    jobs = [(k, col, iso, g.year.values, g[col].values, end) for k, cols in S.items() for col in cols for iso, g in D.dropna(subset=[col]).groupby("iso3")]
    with Pool() as pool: F = pd.DataFrame([f for f in pool.map(fit, jobs, chunksize=8) if f])
    F = F.join(reg, on="iso3")
    for (col, r), g in F.groupby(["col", "region_name"]):       # EB pooling of drift
        d, v = g.a1, g.P11.clip(lower=1e-6); mu = np.average(d, weights=1 / v); tau2 = max(d.var() - v.mean(), 1e-4) if len(g) > 2 else 0.05
        pv = 1 / (1 / v + 1 / tau2); F.loc[g.index, "a1"] = pv * (d / v + mu / tau2); F.loc[g.index, "P01"] = g.P01 * np.sqrt(pv / v); F.loc[g.index, "P11"] = pv
    return F

def sim_level(f, floor, H, NS=4000):
    cov = np.array([[f.P00, f.P01], [f.P01, f.P11 + floor ** 2]]) + 1e-9 * np.eye(2)
    L = rng.multivariate_normal([f.a0, f.a1], cov, NS, method="eigh"); lev = L[:, 0].copy(); out = np.empty((H, NS))
    for h in range(H):
        lev = np.minimum(lev + L[:, 1] + rng.normal(0, f.sl, NS), 100.0); out[h] = lev
    return out

if __name__ == "__main__":
    # ---- backtest + calibration of rural-level drift floors ----
    Fb = run_fits(2014); truth = P[P.year == 2023].set_index("iso3")
    rows = []
    for f in Fb[Fb.col.str.endswith("_rural") & (Fb.key != "jobs")].itertuples():
        if f.iso3 not in truth.index or pd.isna(truth.loc[f.iso3, f.col]): continue
        p = sim_level(f, 0.0, 9, 2000)[-1]
        rows.append(dict(key=f.key, iso3=f.iso3, truth=truth.loc[f.iso3, f.col], med=np.median(p), w0=(np.quantile(p, .9) - np.quantile(p, .1)) / 2.563, start=f.a0))
    B = pd.DataFrame(rows); B["err"] = B.truth - B.med
    isos = B.iso3.unique(); rng.shuffle(isos); A = set(isos[: len(isos) // 2]); FLOOR = {"jobs": 0.30}; cal = []
    for k, g in B.groupby("key"):
        ga, gb = g[g.iso3.isin(A)], g[~g.iso3.isin(A)]
        fl_a = (ga.err.quantile(.9) - ga.err.quantile(.1)) / 2.563 / 9
        cov = (gb.err.abs() <= 1.2816 * np.sqrt(gb.w0 ** 2 + (9 * fl_a) ** 2)).mean()
        FLOOR[k] = (g.err.quantile(.9) - g.err.quantile(.1)) / 2.563 / 9
        cal.append(dict(series=k, n=len(g), raw_cover80=(g.err.abs() <= 1.2816 * g.w0).mean(), heldout_cover80=cov, MAE_model=g.err.abs().mean(),
                        MAE_nochange=(g.truth - g.start).abs().mean(), drift_floor=FLOOR[k]))
    C = pd.DataFrame(cal).round(3); print(C.to_string(index=False)); C.to_csv(OUT / "fpt_level_backtest.csv", index=False)
    # ---- forward from 2024 ----
    F = run_fits(2024); H = 2100 - 2024; yrs = 2024 + np.arange(1, H + 1); out = []
    for k, (rc, uc) in S.items():
        R = F[F.col == rc].set_index("iso3"); U = F[F.col == uc].set_index("iso3")
        for iso in R.index.intersection(U.index):
            f, u = R.loc[iso], U.loc[iso]; zstar = min(u.a0, 100.0)
            base = dict(series=k, iso3=iso, country=f.country_name, region=f.region_name, income=f.income_level_name, rural_2024=f.a0, urban_2024=u.a0)
            if f.a0 >= zstar - 0.5: out.append({**base, "status": "rural already at urban 2024 level"}); continue
            paths = sim_level(f, FLOOR[k], H)
            z = np.minimum(rng.normal(u.a0, np.sqrt(max(u.P00, 0)), paths.shape[1]), 100.0)
            hit = paths >= z[None, :] - 0.5; T = np.where(hit.any(0), yrs[hit.argmax(0)], np.inf)
            med = np.median(T)
            out.append({**base, "p_by_2030": (T <= 2030).mean(), "p_by_2050": (T <= 2050).mean(), "p_by_2100": (T <= 2100).mean(),
                        "median_T_year": np.nan if np.isinf(med) else med, "median_wait_years": np.nan if np.isinf(med) else med - 2024,
                        "status": "likely by 2030" if (T <= 2030).mean() >= .5 else "likely by 2050" if (T <= 2050).mean() >= .5
                                  else "after 2050" if (T <= 2100).mean() >= .5 else "unlikely within forecast horizon (2100)"})
    O = pd.DataFrame(out); O.to_csv(OUT / "fpt_level_rural_reaches_urban2024.csv", index=False)
    print(pd.crosstab(O.series, O.status).to_string())
    g = O.dropna(subset=["p_by_2030"])
    print(g.groupby(["series"])[["p_by_2030", "p_by_2050", "median_wait_years"]].median().round(2).to_string())
    print(g.groupby(["series", "region"])[["p_by_2030", "p_by_2050", "median_wait_years"]].median().round(2).to_string())
