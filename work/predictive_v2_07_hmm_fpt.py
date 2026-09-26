"""
Step 3d — HMM-driven first passage, with backtest.
Engine: pooled 3-regime Gaussian HMM on 3-yr window velocities (fit only on windows observed by the origin).
Start regime ~ country's filtered posterior at its last window; regime chain ~ HMM transition matrix;
v ~ N(mu_regime, sd_regime); G_{k+1} = G_k - 3 v.
Backtest origins 2012 (4 steps) and 2015 (3 steps) vs truth 2024; compare with no-change and previous regime model.
Forward run from 2024 to 2099: P(halve 2024 gap by 2030/2050), P(near parity G<=0.1 by 2050/2099), median years.
"""
from pathlib import Path
import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from hmmlearn.hmm import GaussianHMM
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "predictive_v2"
rng = np.random.default_rng(11)
P = pd.read_csv(OUT / "panel_v2.csv.gz")
NAMES = ["Progressing", "Volatile", "Stuck"]   # ordered by emission sd rank below

def fit_hmm(origin):
    starts = [y for y in range(2003, 2022, 3) if y + 3 <= origin]
    W = P[P.year.isin(starts)].dropna(subset=["target_v_employment"]).sort_values(["iso3", "year"]).copy()
    W = W[W.groupby("iso3").year.transform(lambda y: (y.diff().fillna(3) == 3).all())]
    X = (W.target_v_employment.values * 1000).reshape(-1, 1); L = W.groupby("iso3", sort=False).size().values
    best = None
    for seed in range(20):
        m = GaussianHMM(3, covariance_type="diag", n_iter=500, random_state=seed)
        try: m.fit(X, L); ll = m.score(X, L)
        except Exception: continue
        if best is None or ll > best[0]: best = (ll, m)
    m = best[1]
    post = m.predict_proba(X, L)
    W["_i"] = range(len(W)); lastpost = {iso: post[g._i.iloc[-1]] for iso, g in W.groupby("iso3")}
    return m, lastpost

def simulate(m, p0, G0, steps, NS=4000):
    mu = m.means_.ravel() / 1000; sd = np.sqrt(m.covars_.ravel()) / 1000; A = m.transmat_
    st = rng.choice(3, NS, p=p0 / p0.sum()); G = np.full(NS, G0); paths = []
    for k in range(steps):
        st = (rng.random(NS)[:, None] > A[st].cumsum(1)).sum(1)
        G = G - 3 * rng.normal(mu[st], sd[st]); paths.append(G.copy())
    return np.array(paths)   # steps x NS

truth = P[P.year == 2024].set_index("iso3").gap_employment_tr
if "--forward-only" not in sys.argv:
    rows = []
    for origin in (2012, 2015):
        m, lastpost = fit_hmm(origin); steps = (2024 - origin) // 3
        G0s = P[P.year == origin].set_index("iso3").gap_employment_tr
        for iso, p0 in lastpost.items():
            if iso not in truth.index or pd.isna(truth[iso]) or pd.isna(G0s.get(iso)): continue
            G0 = G0s[iso]; G = simulate(m, p0, G0, steps)[-1]; y = truth[iso]
            rows.append(dict(origin=origin, iso3=iso, G0=G0, truth=y, med=np.median(G), lo80=np.quantile(G, .1), hi80=np.quantile(G, .9),
                             pit=(G < y).mean(), p_halved=(G <= G0 / 2).mean() if G0 > 0.1 else np.nan,
                             y_halved=float(y <= G0 / 2) if G0 > 0.1 else np.nan, p_widened=(G > G0).mean(), y_widened=float(y > G0)))
    R = pd.DataFrame(rows); R.to_csv(OUT / "backtest_fpt_hmm.csv", index=False)
    S = R.groupby("origin").apply(lambda g: pd.Series(dict(n=len(g), MAE_hmm=(g.med - g.truth).abs().mean(), MAE_nochange=(g.G0 - g.truth).abs().mean(),
          cover80=((g.truth >= g.lo80) & (g.truth <= g.hi80)).mean(), mean_p_halved=g.p_halved.mean(), obs_halved=g.y_halved.mean(),
          brier_halved=((g.p_halved - g.y_halved) ** 2).mean(), brier_widened=((g.p_widened - g.y_widened) ** 2).mean(),
          brier_widened_clim=g.y_widened.mean() * (1 - g.y_widened.mean())))).round(3)
    print(S.T.to_string()); S.to_csv(OUT / "backtest_fpt_hmm_summary.csv")
    print("PIT deciles:", R.groupby("origin").pit.apply(lambda x: np.round(np.histogram(x, 10, (0, 1))[0] / len(x), 2).tolist()).to_dict())

# forward from 2024
m, lastpost = fit_hmm(2025)
meta = P[P.year == 2024].set_index("iso3")[["country_name", "region_name", "income_level_name", "gap_employment_tr"]]
order = np.argsort(np.sqrt(m.covars_.ravel()))   # low sd = Stuck, mid = Progressing, high = Volatile
lab = {order[0]: "Stuck", order[1]: "Progressing", order[2]: "Volatile"}
out = []
for iso, p0 in lastpost.items():
    if iso not in meta.index or pd.isna(meta.gap_employment_tr[iso]): continue
    G0 = meta.gap_employment_tr[iso]; r = dict(iso3=iso, country=meta.country_name[iso], region=meta.region_name[iso], income=meta.income_level_name[iso],
          gap_2024=G0, regime_2024=lab[int(np.argmax(p0))], p_regime_2024=float(p0.max()))
    if G0 <= 0.1: r["status"] = "near parity already"; out.append(r); continue
    paths = simulate(m, p0, G0, 25); yrs = 2024 + 3 * np.arange(1, 26)
    def fpt(th):
        hit = paths <= th; first = np.where(hit.any(0), yrs[hit.argmax(0)], np.inf); return first
    Th, Tp = fpt(G0 / 2), fpt(0.1)
    med = lambda T: np.nan if np.isinf(np.median(T)) else float(np.median(T))
    r.update(p_halve_by_2030=(Th <= 2030).mean(), p_halve_by_2050=(Th <= 2051).mean(), median_year_halve=med(Th),
             p_parity_by_2050=(Tp <= 2051).mean(), p_parity_by_2099=(Tp <= 2099).mean(), median_year_parity=med(Tp),
             p_wider_in_2051=(paths[8] > G0).mean())
    r["status"] = "likely halves by 2050" if r["p_halve_by_2050"] >= .5 else ("unlikely to halve this century" if (Th <= 2099).mean() < .5 else "halves after 2050")
    out.append(r)
F = pd.DataFrame(out); F.to_csv(OUT / "first_passage_hmm.csv", index=False)
print("\n", F.status.value_counts().to_string())
g = F.dropna(subset=["p_halve_by_2050"])
print(g.groupby("region")[["gap_2024", "p_halve_by_2030", "p_halve_by_2050", "p_parity_by_2099", "p_wider_in_2051"]].median().round(2).to_string())
print(g.groupby("regime_2024")[["p_halve_by_2050", "p_parity_by_2099"]].median().round(2).to_string())
print(g.sort_values("gap_2024", ascending=False)[["country", "gap_2024", "regime_2024", "p_halve_by_2050", "p_parity_by_2099"]].head(12).round(2).to_string(index=False))
