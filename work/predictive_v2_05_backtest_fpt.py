"""
Backtest of the regime-switching first-passage model.
Origins 2012 (4 steps -> 2024) and 2015 (3 steps -> 2024). Only windows fully observed by the origin are used for fitting
(window t..t+3 with t+3 <= origin). Forecast target: employment gap in 2024 (trailing 3y mean) and event "gap halved".
Compare against: (1) no change, (2) own-past-velocity drift (last window's v held constant).
Metrics: MAE of median forecast, 80% interval coverage, PIT histogram, Brier for 'halved by 2024' and 'widened by 2024'.
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "predictive_v2"
rng = np.random.default_rng(7)
P = pd.read_csv(OUT / "panel_v2.csv.gz")
S = ["Closing", "Flat", "Widening"]; IDX = {s: i for i, s in enumerate(S)}; C = 0.005

def tmat(T):
    M = pd.crosstab(T.state, T.next_state).reindex(index=S, columns=S, fill_value=0)
    return M.div(M.sum(1).replace(0, np.nan), axis=0).fillna(1 / 3)

def windows(origin):
    starts = [y for y in range(2003, 2022, 3) if y + 3 <= origin]
    W = P[P.year.isin(starts)].dropna(subset=["target_v_employment"]).sort_values(["iso3", "year"]).copy()
    v = W.target_v_employment
    W["state"] = np.select([v > C, v < -C], ["Closing", "Widening"], "Flat")
    W["next_state"] = W.groupby("iso3")["state"].shift(-1); W["next_year"] = W.groupby("iso3")["year"].shift(-1)
    return W, W[W.next_year == W.year + 3]

truth = P[P.year == 2024].set_index("iso3").gap_employment_tr
rows = []
for origin in (2012, 2015):
    W, T = windows(origin); M = tmat(T); steps = (2024 - origin) // 3
    pool_inc = {g: tmat(t) for g, t in T.groupby("income_level_name")}
    vdist = {(g, s): t.target_v_employment.values for (g, s), t in W.groupby(["income_level_name", "state"])}
    vall = {s: t.target_v_employment.values for s, t in W.groupby("state")}
    last_w = W[W.year == origin - 3].set_index("iso3")
    G0s = P[P.year == origin].set_index("iso3")
    for iso in last_w.index:
        if iso not in truth.index or pd.isna(truth[iso]) or pd.isna(G0s.gap_employment_tr.get(iso)): continue
        g = last_w.income_level_name[iso]; prior = pool_inc.get(g, M)
        Ti = T[T.iso3 == iso]
        cnt = pd.crosstab(Ti.state, Ti.next_state).reindex(index=S, columns=S, fill_value=0)
        Pc = ((cnt + 4 * prior).div((cnt + 4 * prior).sum(1), axis=0)).values
        G0 = G0s.gap_employment_tr[iso]; NS = 4000
        st = np.full(NS, IDX[last_w.state[iso]]); G = np.full(NS, G0)
        for k in range(steps):
            u = rng.random(NS); st = (u[:, None] > Pc[st].cumsum(1)).sum(1)
            v = np.empty(NS)
            for s in range(3):
                m = st == s; pool = vdist.get((g, S[s]), vall[S[s]]); pool = pool if len(pool) >= 15 else vall[S[s]]
                v[m] = rng.choice(pool, m.sum())
            G = G - 3 * v
        y = truth[iso]; vlast = last_w.target_v_employment[iso]
        rows.append(dict(origin=origin, iso3=iso, income=g, G0=G0, truth=y,
                         med=np.median(G), lo80=np.quantile(G, .1), hi80=np.quantile(G, .9), pit=(G < y).mean(),
                         p_halved=(G <= G0 / 2).mean() if G0 > 0.1 else np.nan, y_halved=float(y <= G0 / 2) if G0 > 0.1 else np.nan,
                         p_widened=(G > G0).mean(), y_widened=float(y > G0),
                         naive_nochange=G0, naive_drift=G0 - 3 * steps * vlast))
R = pd.DataFrame(rows); R.to_csv(OUT / "backtest_fpt_regime.csv", index=False)
def summ(g):
    return pd.Series(dict(n=len(g),
        MAE_model=(g.med - g.truth).abs().mean(), MAE_nochange=(g.naive_nochange - g.truth).abs().mean(),
        MAE_drift=(g.naive_drift - g.truth).abs().mean(),
        cover80=((g.truth >= g.lo80) & (g.truth <= g.hi80)).mean(),
        brier_widened=((g.p_widened - g.y_widened) ** 2).mean(), base_widened=g.y_widened.mean(),
        brier_widened_clim=g.y_widened.mean() * (1 - g.y_widened.mean()),
        brier_halved=((g.p_halved - g.y_halved) ** 2).mean(), base_halved=g.y_halved.mean(),
        mean_p_halved=g.p_halved.mean()))
Sm = R.groupby("origin").apply(summ).round(3); print(Sm.T.to_string()); Sm.to_csv(OUT / "backtest_fpt_regime_summary.csv")
print("\nPIT deciles (ideal 0.1 each):"); print(R.groupby("origin").pit.apply(lambda x: np.histogram(x, bins=10, range=(0, 1))[0] / len(x)).apply(lambda a: np.round(a, 2)).to_string())
print("\ncoverage by income:"); print(R.groupby(["origin", "income"]).apply(lambda g: ((g.truth >= g.lo80) & (g.truth <= g.hi80)).mean()).round(2).unstack().to_string())
