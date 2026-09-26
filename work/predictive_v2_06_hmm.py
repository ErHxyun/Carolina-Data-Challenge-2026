"""
Step 3c — Hidden Markov Model of latent progress regimes.
Observation: 3-year window velocity v (SD of employment gap closed per year), windows starting 2003..2021 (7 per country).
Pooled Gaussian HMM (shared emission means/variances and transition matrix), K = 2..4 compared by BIC, 20 random restarts.
Outputs: regime parameters, transition matrix (3-year steps), decoded regimes per country-window, regime shares by period/income.
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from hmmlearn.hmm import GaussianHMM
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "predictive_v2"
P = pd.read_csv(OUT / "panel_v2.csv.gz")
W = P[P.year.isin(range(2003, 2022, 3))].dropna(subset=["target_v_employment"]).sort_values(["iso3", "year"]).copy()
# keep countries with contiguous windows
W["gap_ok"] = W.groupby("iso3").year.diff().fillna(3) == 3
bad = W.loc[~W.gap_ok, "iso3"].unique(); W = W[~W.iso3.isin(bad)]
X = (W.target_v_employment.values * 1000).reshape(-1, 1)           # milli-SD per year
lengths = W.groupby("iso3", sort=False).size().values
fits = {}
for K in (2, 3, 4):
    best = None
    for seed in range(20):
        m = GaussianHMM(n_components=K, covariance_type="diag", n_iter=500, random_state=seed, init_params="stmc")
        try: m.fit(X, lengths)
        except Exception: continue
        ll = m.score(X, lengths)
        if best is None or ll > best[0]: best = (ll, m)
    ll, m = best; npar = K * (K - 1) + (K - 1) + 2 * K
    fits[K] = (m, ll, -2 * ll + npar * np.log(len(X)))
    print(f"K={K}: logL={ll:.1f}  BIC={fits[K][2]:.1f}  means={np.sort(m.means_.ravel()).round(1)}")
K = 3; m = fits[K][0]
order = np.argsort(-m.means_.ravel())                       # 0 = fastest closing
names = {order[0]: "Catching up", order[1]: "Stalled", order[2]: "Falling behind"}
reg = pd.DataFrame({"regime": [names[i] for i in order], "mean_v_milliSD": m.means_.ravel()[order],
                    "sd_v_milliSD": np.sqrt(m.covars_.ravel()[order])})
TM = pd.DataFrame(m.transmat_[np.ix_(order, order)], index=reg.regime, columns=reg.regime)
start = pd.Series(m.startprob_[order], index=reg.regime)
w, v = np.linalg.eig(TM.values.T); stat = np.real(v[:, np.argmin(abs(w - 1))]); stat = stat / stat.sum()
reg["stationary_share"] = stat; reg["expected_spell_years"] = 3 / (1 - np.diag(TM.values))
print(reg.round(3).to_string(index=False)); print(TM.round(3).to_string())
post = m.predict_proba(X, lengths)[:, order]
W[["p_catch", "p_stall", "p_fall"]] = post
W["regime"] = np.array(reg.regime)[post.argmax(1)]
W["window"] = W.year.astype(str) + "–" + (W.year + 3).astype(str)
reg.to_csv(OUT / "hmm_regimes.csv", index=False); TM.to_csv(OUT / "hmm_transition_matrix.csv")
W[["iso3", "country_name", "region_name", "income_level_name", "year", "window", "target_v_employment", "p_catch", "p_stall", "p_fall", "regime"]].to_csv(OUT / "hmm_decoded.csv", index=False)
byper = pd.crosstab(W.window, W.regime, normalize="index")[list(reg.regime)].round(3); print("\nregime share by window:\n", byper.to_string()); byper.to_csv(OUT / "hmm_share_by_window.csv")
byinc = pd.crosstab(W.income_level_name, W.regime, normalize="index")[list(reg.regime)].round(3); print("\nby income:\n", byinc.to_string()); byinc.to_csv(OUT / "hmm_share_by_income.csv")
# empirical transitions of decoded regimes by income (persistence of falling behind)
W["next_regime"] = W.groupby("iso3").regime.shift(-1)
tr = W.dropna(subset=["next_regime"])
pers = tr.groupby("income_level_name").apply(lambda g: pd.Series({
    "P(stay Falling behind)": (g[g.regime == "Falling behind"].next_regime == "Falling behind").mean(),
    "P(Falling->Catching)": (g[g.regime == "Falling behind"].next_regime == "Catching up").mean(),
    "P(stay Catching up)": (g[g.regime == "Catching up"].next_regime == "Catching up").mean(),
    "n_falling": int((g.regime == "Falling behind").sum())})).round(3)
print("\n", pers.to_string()); pers.to_csv(OUT / "hmm_persistence_by_income.csv")
# countries never in catching-up regime
never = W.groupby(["iso3", "country_name", "region_name"]).regime.apply(lambda r: (r == "Catching up").sum()).reset_index(name="n_catch")
nv = never[never.n_catch == 0]; print(f"\n{len(nv)} of {never.shape[0]} economies never in a catching-up regime 2003–2024; by region:\n", nv.region_name.value_counts().to_string())
never.to_csv(OUT / "hmm_catchup_counts.csv", index=False)
