"""
Framework item 2, full Bayesian version:
    G_{c,t} = G_{c,t-1} - kappa_c G_{c,t-1} + beta' X_{c,t-1} + eta_{c,t},   eta ~ N(0, sigma_c^2)
    kappa_c ~ N(mu_r, tau_r^2)   (r = region)     mu_r ~ N(0, 0.2^2)   tau_r^2 ~ IG(2, 0.001)
    beta ~ N(0, 10^2 I)          sigma_c^2 ~ IG(1, 0.01)
Gibbs sampler (all full conditionals conjugate). X (standardized, lagged): log GDP pc, fertility, urban share, internet use.
Outputs from ONE posterior: P(kappa_c > 0 | data), half-life, beta, and posterior-predictive P(G_2030 < 0.5 G_2024 | data)
(X held at latest values). Backtest: fit through 2014, 80% posterior-predictive interval for 2023.
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"; CMB = ROOT / "outputs" / "world_bank_sources" / "combined"
P = pd.read_csv(OUT / "rural_urban_panel.csv.gz")
w = pd.read_parquet(CMB / "002_WDI_wide.parquet", columns=["iso3", "year", "is_aggregate", "IT.NET.USER.ZS", "SP.URB.TOTL.IN.ZS"])
w = w[~w.is_aggregate].drop(columns="is_aggregate").rename(columns={"IT.NET.USER.ZS": "internet", "SP.URB.TOTL.IN.ZS": "urban_share"})
P = P.merge(w, on=["iso3", "year"], how="left").sort_values(["iso3", "year"])
P["log_gdppc"] = np.log(P.gdppc_ppp)
XC = ["log_gdppc", "fertility", "urban_share", "internet"]
for c in XC: P[c] = P.groupby("iso3")[c].ffill(limit=2)
rng = np.random.default_rng(42)

def build(series, end):
    D = P[P.year.between(2000, end)].copy()
    g = D.groupby("iso3")
    D["G_lag"] = g[series].shift(1); D["y"] = D[series] - D.G_lag; D["gap_ok"] = g.year.diff() == 1
    for c in XC: D[c + "_l"] = g[c].shift(1)
    D = D[D.gap_ok & (D.G_lag.abs() >= 1)].dropna(subset=["y", "G_lag"] + [c + "_l" for c in XC])
    D = D[D.groupby("iso3").y.transform("size") >= 5]
    return D

def gibbs(D, n_iter=4000, burn=1000):
    Xraw = D[[c + "_l" for c in XC]].values; mu_x, sd_x = Xraw.mean(0), Xraw.std(0); X = (Xraw - mu_x) / sd_x
    y = D.y.values; x = D.G_lag.values
    cid, cidx = np.unique(D.iso3.values, return_inverse=True); C = len(cid)
    creg = D.groupby("iso3").region_name.first().reindex(cid).fillna("NA").values
    rid, ridx = np.unique(creg, return_inverse=True); R = len(rid)
    k = np.zeros(C); beta = np.zeros(X.shape[1]); s2 = np.full(C, 1.0); mu = np.zeros(R); t2 = np.full(R, 0.001)
    nc = np.bincount(cidx, minlength=C); keep = []
    for it in range(n_iter):
        r = y - X @ beta
        prec = np.bincount(cidx, x * x, C) / s2 + 1 / t2[ridx]
        mean = (np.bincount(cidx, -x * r, C) / s2 + mu[ridx] / t2[ridx]) / prec
        k = mean + rng.standard_normal(C) / np.sqrt(prec)
        yt = y + k[cidx] * x; wv = 1 / s2[cidx]
        A = (X * wv[:, None]).T @ X + np.eye(X.shape[1]) / 100; b = (X * wv[:, None]).T @ yt
        L = np.linalg.cholesky(A); beta = np.linalg.solve(A, b) + np.linalg.solve(L.T, rng.standard_normal(X.shape[1]))
        res = y + k[cidx] * x - X @ beta
        s2 = 1 / rng.gamma(1 + nc / 2, 1 / (0.01 + np.bincount(cidx, res * res, C) / 2))
        for j in range(R):
            m = ridx == j; kj = k[m]; n = m.sum()
            pv = 1 / (n / t2[j] + 1 / 0.04); mu[j] = pv * kj.sum() / t2[j] + rng.standard_normal() * np.sqrt(pv)
            t2[j] = 1 / rng.gamma(2 + n / 2, 1 / (0.001 + ((kj - mu[j]) ** 2).sum() / 2))
        if it >= burn and it % 3 == 0: keep.append((k.copy(), beta.copy(), s2.copy()))
    K = np.array([a for a, _, _ in keep]); Bt = np.array([b for _, b, _ in keep]); S2 = np.array([c for _, _, c in keep])
    return dict(cid=cid, K=K, B=Bt, S2=S2, mu_x=mu_x, sd_x=sd_x)

def predict(fitres, series, end, horizon_years, NS=1000, phi=0.0):
    """posterior predictive of G at end+h for each country, X held at latest values (as of `end`)"""
    last = P[P.year <= end].dropna(subset=[series]).groupby("iso3").tail(1).set_index("iso3")
    Xl = P[P.year <= end].groupby("iso3")[XC].last()
    out = {}
    idx = rng.choice(len(fitres["K"]), NS)
    for j, iso in enumerate(fitres["cid"]):
        if iso not in last.index or iso not in Xl.index or Xl.loc[iso].isna().any(): continue
        G0 = last.loc[iso, series]; y0 = int(last.loc[iso, "year"]); xs = (Xl.loc[iso].values - fitres["mu_x"]) / fitres["sd_x"]
        k = fitres["K"][idx, j]; drift = fitres["B"][idx] @ xs + rng.standard_normal(NS) * phi; sd = np.sqrt(fitres["S2"][idx, j])   # phi: calibrated structural drift uncertainty
        G = np.full(NS, G0); traj = {}
        for yr in range(y0 + 1, max(horizon_years) + 1):
            G = G - k * G + drift + rng.standard_normal(NS) * sd; traj[yr] = G.copy()
        out[iso] = (G0, y0, traj)
    return out

rows_b, rows_c, rows_bt, cal = [], [], [], []
for series in ["infra_gap", "cooking_gap", "water_gap", "sanitation_gap"]:
    # ---- backtest + calibration of phi ----
    Db = build(series, 2014); fb = gibbs(Db, 3000, 800); pb = predict(fb, series, 2014, [2023])
    truth = P[P.year == 2023].set_index("iso3")[series]; bt = []
    for iso, (G0, y0, tr) in pb.items():
        if iso in truth.index and not pd.isna(truth[iso]) and y0 == 2014:
            g = tr[2023]; bt.append(dict(series=series, iso3=iso, truth=truth[iso], med=np.median(g), w0=(np.quantile(g, .9) - np.quantile(g, .1)) / 2.563, G0=G0))
    bt = pd.DataFrame(bt); bt["err"] = bt.truth - bt.med
    isos = bt.iso3.unique(); rng.shuffle(isos); A = set(isos[: len(isos) // 2])
    ga, gb = bt[bt.iso3.isin(A)], bt[~bt.iso3.isin(A)]
    phi_a = (ga.err.quantile(.9) - ga.err.quantile(.1)) / 2.563 / 9
    heldout = (gb.err.abs() <= 1.2816 * np.sqrt(gb.w0 ** 2 + (9 * phi_a) ** 2)).mean()
    phi = (bt.err.quantile(.9) - bt.err.quantile(.1)) / 2.563 / 9
    cal.append(dict(series=series, n=len(bt), raw_cover80=(bt.err.abs() <= 1.2816 * bt.w0).mean(), heldout_cover80_after_cal=heldout,
                    MAE_model=bt.err.abs().mean(), MAE_nochange=(bt.G0 - bt.truth).abs().mean(), phi_pp_per_yr=phi))
    # ---- forward ----
    D = build(series, 2024); fr = gibbs(D)
    for i, name in enumerate(XC):
        b = fr["B"][:, i]; rows_b.append(dict(series=series, covariate=name, beta_mean=b.mean(), lo95=np.quantile(b, .025), hi95=np.quantile(b, .975), p_positive=(b > 0).mean()))
    pred = predict(fr, series, 2024, [2030, 2050], phi=phi)
    reg = P.drop_duplicates("iso3").set_index("iso3")
    for j, iso in enumerate(fr["cid"]):
        k = fr["K"][:, j]; pk = (k > 0).mean(); r = dict(series=series, iso3=iso, country=reg.loc[iso, "country_name"], region=reg.loc[iso, "region_name"],
             kappa_median=np.median(k), kappa_lo95=np.quantile(k, .025), kappa_hi95=np.quantile(k, .975), p_kappa_pos=pk,
             half_life=np.log(2) / np.median(k) if pk >= .9 else np.nan)
        if iso in pred:
            G0, y0, tr = pred[iso]; r.update(gap_latest=G0, year_latest=y0,
                p_halve_2030=(tr[2030] < 0.5 * G0).mean() if G0 > 2 else np.nan, p_halve_2050=(tr[2050] < 0.5 * G0).mean() if G0 > 2 else np.nan,
                p_wider_2030=(tr[2030] > G0).mean())
        rows_c.append(r)
    print(series, "done", len(D), "obs", len(fr["cid"]), "economies", flush=True)
Bt = pd.DataFrame(rows_b); Ct = pd.DataFrame(rows_c)
Bt.round(4).to_csv(OUT / "bayes_kappa_beta.csv", index=False); Ct.to_csv(OUT / "bayes_kappa_by_country.csv", index=False)
CAL = pd.DataFrame(cal).round(3); print("\nbacktest 2014->2023 and calibration:\n", CAL.to_string(index=False)); CAL.to_csv(OUT / "bayes_kappa_backtest.csv", index=False)
print("\nbeta (effect on annual gap change, pp per SD; negative = helps close):\n", Bt.round(3).to_string(index=False))
S = Ct.groupby("series").agg(economies=("iso3", "size"), kappa_med=("kappa_median", "median"), share_p_ge90=("p_kappa_pos", lambda p: (p >= .9).mean()),
      share_p_le10=("p_kappa_pos", lambda p: (p <= .1).mean()), half_life_med=("half_life", "median"), p_halve_2030_med=("p_halve_2030", "median"),
      p_halve_2050_med=("p_halve_2050", "median")).round(3)
print("\n", S.to_string()); S.to_csv(OUT / "bayes_kappa_summary.csv")
