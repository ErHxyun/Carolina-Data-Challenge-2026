"""
Rural–urban step 4: HMM regimes of the urban–rural gap.
Observation: annual convergence speed c_t = -(G_t - G_{t-1}) in pp/yr (positive = rural catching up), 2001-2024.
Pooled 3-state Gaussian HMM per series (infra composite, clean cooking), 20 restarts; states ordered by mean:
Converging / Stalled / Diverging. Outputs: regime params, transition matrix, decoded regimes, P(regime in latest year),
P(enter Converging next year), and a covariate model of transitions (softmax-style via binary logits, clustered SE).
"""
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm, warnings; warnings.filterwarnings("ignore")
from hmmlearn.hmm import GaussianHMM
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"
P = pd.read_csv(OUT / "rural_urban_panel.csv.gz").sort_values(["iso3", "year"])
P = P[P.year.between(2000, 2024)]
P["log_gdppc"] = np.log(P.gdppc_ppp); P["gdp_growth"] = P.groupby("iso3").gdppc_ppp.pct_change() * 100
LAB = ["Converging", "Stalled", "Diverging"]
summ = []
for s in ["infra_gap", "cooking_gap"]:
    D = P.dropna(subset=[s]).copy()
    D = D[D.groupby("iso3").year.transform(lambda y: (y.diff().fillna(1) == 1).all())]
    D["c"] = -D.groupby("iso3")[s].diff(); D = D.dropna(subset=["c"])
    # only country-years with a real gap to close (>= 2 pp) and rural coverage below saturation (< 97%)
    rur = s.replace("_gap", "_rural"); D = D[(D[s].abs() >= 2) & (D[rur] < 97)]
    D = D[D.groupby("iso3").year.transform(lambda y: (y.diff().fillna(1) == 1).all())]
    D = D[D.groupby("iso3").c.transform("size") >= 10]
    X = D.c.values.reshape(-1, 1); L = D.groupby("iso3", sort=False).size().values
    best = None
    for seed in range(20):
        m = GaussianHMM(3, covariance_type="diag", n_iter=500, random_state=seed)
        try: m.fit(X, L); ll = m.score(X, L)
        except Exception: continue
        if best is None or ll > best[0]: best = (ll, m)
    m = best[1]; o = np.argsort(-m.means_.ravel())
    A = pd.DataFrame(m.transmat_[np.ix_(o, o)], index=LAB, columns=LAB)
    reg = pd.DataFrame({"regime": LAB, "mean_pp_per_yr": m.means_.ravel()[o], "sd": np.sqrt(m.covars_.ravel()[o]),
                        "expected_spell_yrs": 1 / (1 - np.diag(A.values))})
    w, v = np.linalg.eig(A.values.T); st = np.real(v[:, np.argmin(abs(w - 1))]); reg["stationary_share"] = st / st.sum()
    post = m.predict_proba(X, L)[:, o]; D[["p_conv", "p_stall", "p_div"]] = post; D["regime"] = np.array(LAB)[post.argmax(1)]
    print(f"\n==== {s} ({D.iso3.nunique()} economies) ====\n", reg.round(3).to_string(index=False), "\n", A.round(3).to_string())
    reg.to_csv(OUT / f"hmm_{s}_regimes.csv", index=False); A.to_csv(OUT / f"hmm_{s}_transitions.csv")
    # latest-year regime probabilities and next-year entry probability into Converging
    last = D.groupby("iso3").tail(1).copy()
    pnext = last[["p_conv", "p_stall", "p_div"]].values @ A.values
    last["p_converging_next_year"] = pnext[:, 0]; last["p_diverging_next_year"] = pnext[:, 2]
    last[["iso3", "country_name", "region_name", "income_level_name", "year", s, "p_conv", "p_stall", "p_div", "regime",
          "p_converging_next_year", "p_diverging_next_year"]].to_csv(OUT / f"hmm_{s}_latest.csv", index=False)
    D[["iso3", "country_name", "region_name", "year", s, "c", "p_conv", "p_stall", "p_div", "regime"]].to_csv(OUT / f"hmm_{s}_decoded.csv", index=False)
    print("latest regime by region:\n", pd.crosstab(last.region_name, last.regime, normalize="index").reindex(columns=LAB).round(2).to_string())
    print("regime share by period:\n", pd.crosstab(pd.cut(D.year, [2000, 2008, 2016, 2024], labels=["2001-08", "2009-16", "2017-24"]), D.regime, normalize="index").reindex(columns=LAB).round(3).to_string())
    # covariates of transitions (next year's regime)
    D["next"] = D.groupby("iso3").regime.shift(-1)
    T = D.dropna(subset=["next", "log_gdppc", "gdp_growth", "fertility", "rural_pop_share"]).copy()
    for cv in ["log_gdppc", "gdp_growth", "fertility", "rural_pop_share"]: T[cv] = (T[cv] - T[cv].mean()) / T[cv].std()
    T["from_stalled"] = (T.regime == "Stalled").astype(float); T["from_div"] = (T.regime == "Diverging").astype(float)
    for tgt in ["Converging", "Diverging"]:
        y = (T.next == tgt).astype(float); Xm = sm.add_constant(T[["from_stalled", "from_div", "log_gdppc", "gdp_growth", "fertility", "rural_pop_share"]])
        r = sm.Logit(y, Xm).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(T.iso3)[0]})
        orr = pd.DataFrame({"odds_ratio": np.exp(r.params), "p": r.pvalues}).drop("const").round(3)
        orr.to_csv(OUT / f"hmm_{s}_covariates_next_{tgt}.csv"); print(f"next={tgt}:\n", orr.to_string())
