"""
Rural–urban step 3: first passage time of the urban–rural gap (future stochastic waiting time).
Per country x series: local level + deterministic drift state-space model (Kalman; handles missing survey years and
separates measurement noise from true movement), drift partially pooled within region (empirical Bayes).
Simulate 4000 future gap paths from the terminal state distribution + level shocks.
T* = first year the latent gap <= threshold. Thresholds: (a) half of the latest gap, (b) near parity (<= 2 pp; jobs <= 5 pp).
Backtest: fit through 2014, check 2023 (infra) / latest survey (jobs not backtested: too sparse).
Usage: python3 rural_03_fpt.py [fit_end]
"""
from pathlib import Path
import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from multiprocessing import Pool
from statsmodels.tsa.statespace.structural import UnobservedComponents
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"
FIT_END = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 2024
P = pd.read_csv(OUT / "rural_urban_panel.csv.gz")
for c in ["fem_nonag_rural", "fem_nonag_urban", "jobs_gap"]: P[c] = P[c] * 100
SERIES = {"infra_gap": 2.0, "cooking_gap": 2.0, "water_gap": 2.0, "sanitation_gap": 2.0, "jobs_gap": 5.0}
# drift-uncertainty floors (pp/yr) calibrated on the 2014->2023 backtest (held-out half coverage 79-96%);
# jobs: no backtest possible (sparse surveys) -> conservative 0.3 pp/yr
DRIFT_FLOOR = {"cooking_gap": 1.281, "infra_gap": 0.490, "sanitation_gap": 0.176, "water_gap": 0.190, "jobs_gap": 0.30}
if "--nocal" in sys.argv: DRIFT_FLOOR = {k: 0.0 for k in DRIFT_FLOOR}
reg = P.drop_duplicates("iso3").set_index("iso3")[["country_name", "region_name", "income_level_name"]]

def fit_one(args):
    s, iso, years, vals = args
    y = pd.Series(vals, index=years).reindex(range(2000, FIT_END + 1))
    if y.notna().sum() < (4 if s == "jobs_gap" else 8) or y.last_valid_index() < FIT_END - (8 if s == "jobs_gap" else 3): return None
    try:
        r = UnobservedComponents(y.values, level="lldtrend").fit(disp=False, maxiter=200)
    except Exception: return None
    names = list(r.model.param_names)
    sl = np.sqrt(max(r.params[names.index("sigma2.level")], 0)); se = np.sqrt(max(r.params[names.index("sigma2.irregular")], 0))
    return dict(series=s, iso3=iso, a0=r.filtered_state[0, -1], a1=r.filtered_state[1, -1], P00=r.filtered_state_cov[0, 0, -1],
                P01=r.filtered_state_cov[0, 1, -1], P11=r.filtered_state_cov[1, 1, -1], sig_level=sl, sig_irreg=se, n_obs=int(y.notna().sum()),
                last_obs=int(y.last_valid_index()), gap_latest_obs=float(y.dropna().iloc[-1]))

if __name__ == "__main__":
    D = P[P.year.between(2000, FIT_END)]
    jobs = [(s, iso, g.year.values, g[s].values) for s in SERIES for iso, g in D.dropna(subset=[s]).groupby("iso3")]
    with Pool() as pool: fits = [f for f in pool.map(fit_one, jobs, chunksize=8) if f]
    F = pd.DataFrame(fits).join(reg, on="iso3")
    # EB shrink drift within region x series
    for (s, r), g in F.groupby(["series", "region_name"]):
        d, v = g.a1, g.P11.clip(lower=1e-6); mu = np.average(d, weights=1 / v)
        tau2 = max(d.var() - v.mean(), 1e-4) if len(g) > 2 else 0.05
        pv = 1 / (1 / v + 1 / tau2); F.loc[g.index, "a1"] = pv * (d / v + mu / tau2)
        F.loc[g.index, "P01"] = g.P01 * np.sqrt(pv / v); F.loc[g.index, "P11"] = pv
    rng = np.random.default_rng(3); NS = 4000; H = 2100 - FIT_END; yrs = FIT_END + np.arange(1, H + 1)
    rows = []
    for f in F.itertuples():
        G0 = f.a0; th_par = SERIES[f.series]
        base = dict(series=f.series, iso3=f.iso3, country=f.country_name, region=f.region_name, income=f.income_level_name,
                    gap_now=G0, drift_pp_yr=f.a1, n_obs=f.n_obs, last_obs=f.last_obs)
        if G0 <= th_par: rows.append({**base, "status": "at/near parity"}); continue
        cov = np.array([[f.P00, f.P01], [f.P01, f.P11 + DRIFT_FLOOR[f.series] ** 2]]) + 1e-9 * np.eye(2)
        L = rng.multivariate_normal([f.a0, f.a1], cov, NS, method="eigh")
        lev = L[:, 0].copy(); paths = np.empty((H, NS))
        for h in range(H):
            lev = lev + L[:, 1] + rng.normal(0, f.sig_level, NS); paths[h] = lev
        def fpt(th):
            hit = paths <= th; return np.where(hit.any(0), yrs[hit.argmax(0)], np.inf)
        Th, Tp = fpt(G0 / 2), fpt(th_par)
        med = lambda T: np.nan if np.isinf(np.median(T)) else float(np.median(T))
        r = {**base, "p_halve_by_2030": (Th <= 2030).mean(), "p_halve_by_2050": (Th <= 2050).mean(), "median_year_halve": med(Th),
             "p_parity_by_2030": (Tp <= 2030).mean(), "p_parity_by_2050": (Tp <= 2050).mean(), "median_year_parity": med(Tp),
             "p_gap_wider_2030": (paths[2030 - FIT_END - 1] > G0).mean() if 2030 > FIT_END else np.nan,
             "gap_2030_med": np.median(paths[min(2030 - FIT_END, H) - 1]), "gap_2030_lo": np.quantile(paths[min(2030 - FIT_END, H) - 1], .1),
             "gap_2030_hi": np.quantile(paths[min(2030 - FIT_END, H) - 1], .9)}
        if FIT_END < 2023:
            r["pred_2023_med"] = np.median(paths[2023 - FIT_END - 1]); r["pred_2023_lo"] = np.quantile(paths[2023 - FIT_END - 1], .1)
            r["pred_2023_hi"] = np.quantile(paths[2023 - FIT_END - 1], .9); r["G_fit_end"] = G0
        r["status"] = ("likely halves by 2030" if r["p_halve_by_2030"] >= .5 else "likely halves by 2050" if r["p_halve_by_2050"] >= .5
                       else "halving unlikely before 2100" if (Th <= 2099).mean() < .5 else "halves after 2050")
        rows.append(r)
    R = pd.DataFrame(rows); tag = "" if FIT_END >= 2023 else f"_fit{FIT_END}"
    R.to_csv(OUT / f"fpt_rural_urban{tag}.csv", index=False)
    if FIT_END >= 2023:
        print(pd.crosstab(R.series, R.status).to_string())
        g = R.dropna(subset=["p_halve_by_2050"])
        print(g.groupby(["series", "region"])[["gap_now", "p_halve_by_2030", "p_halve_by_2050", "p_parity_by_2050", "p_gap_wider_2030"]].median().round(2).to_string())
    else:
        truth = P[P.year == 2023].set_index("iso3")
        B = R.dropna(subset=["pred_2023_med"]).copy(); B = B[B.series != "jobs_gap"]
        B["truth"] = [truth.loc[i, s] if i in truth.index else np.nan for i, s in zip(B.iso3, B.series)]
        B = B.dropna(subset=["truth"])
        B["cover80"] = (B.truth >= B.pred_2023_lo) & (B.truth <= B.pred_2023_hi)
        B["ae_model"] = (B.pred_2023_med - B.truth).abs(); B["ae_nochange"] = (B.G_fit_end - B.truth).abs()
        B["halved_true"] = B.truth <= B.G_fit_end / 2
        S = B.groupby("series").agg(n=("iso3", "size"), cover80=("cover80", "mean"), MAE_model=("ae_model", "mean"), MAE_nochange=("ae_nochange", "mean")).round(3)
        print(S.to_string()); S.to_csv(OUT / "fpt_backtest_2014.csv")
