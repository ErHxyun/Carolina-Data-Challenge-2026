"""
Framework item 3, covariate-dependent transitions (origin-specific softmax):
    P(S_t = j | S_{t-1} = i, X_{t-1}) = softmax_j(alpha_ij + beta_ij' X_{t-1}),   j in {Converging, Stalled, Diverging}
Regimes = HMM-decoded clean-cooking regimes (rural_04_hmm.py). One multinomial logit per origin state i (base = stay in i),
L2-regularised (C = 1 on standardized X), 95% CIs from a country-cluster bootstrap (300 reps).
Spec A (2001-2024): log GDP pc, fertility, rural population share, internet use (digital access).
Spec B (2011-2024): Spec A + women's account ownership (Findex, carried forward <= 3 years).
Reports odds ratios exp(beta_ij) per +1 SD for each leaving transition i -> j.
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"; CMB = ROOT / "outputs" / "world_bank_sources" / "combined"
H = pd.read_csv(OUT / "hmm_cooking_gap_decoded.csv")[["iso3", "year", "regime"]].sort_values(["iso3", "year"])
P = pd.read_csv(OUT / "rural_urban_panel.csv.gz")[["iso3", "year", "gdppc_ppp", "fertility", "rural_pop_share"]]
w = pd.read_parquet(CMB / "002_WDI_wide.parquet", columns=["iso3", "year", "is_aggregate", "IT.NET.USER.ZS", "FX.OWN.TOTL.FE.ZS"])
w = w[~w.is_aggregate].rename(columns={"IT.NET.USER.ZS": "internet", "FX.OWN.TOTL.FE.ZS": "women_account"}).drop(columns="is_aggregate")
X = P.merge(w, on=["iso3", "year"], how="outer").sort_values(["iso3", "year"])
X["log_gdppc"] = np.log(X.gdppc_ppp)
for c in ["internet", "fertility", "rural_pop_share", "log_gdppc"]: X[c] = X.groupby("iso3")[c].ffill(limit=2)
X["women_account"] = X.groupby("iso3").women_account.ffill(limit=3)
X["year"] = X.year + 1                      # lag: X_{t-1} attached to transition into year t
D = H.copy(); D["prev"] = D.groupby("iso3").regime.shift(1); D["yprev"] = D.groupby("iso3").year.shift(1)
D = D[D.yprev == D.year - 1].merge(X, on=["iso3", "year"], how="left")
STATES = ["Converging", "Stalled", "Diverging"]; rng = np.random.default_rng(8)
SPECS = {"A": ["log_gdppc", "fertility", "rural_pop_share", "internet"], "B": ["log_gdppc", "fertility", "rural_pop_share", "internet", "women_account"]}
rows = []
for spec, cols in SPECS.items():
    d0 = D.dropna(subset=cols + ["prev"]); d0 = d0[d0.year >= (2011 if spec == "B" else 2001)]
    mu, sd = d0[cols].mean(), d0[cols].std()
    for origin in STATES:
        d = d0[d0.prev == origin].copy()
        cats = [s for s in STATES if (d.regime == s).sum() > 0]
        leave = [j for j in cats if j != origin]
        if not leave: continue
        Z = ((d[cols] - mu) / sd).values; y = d.regime.values
        def fit(Zb, yb):
            m = LogisticRegression(C=1.0, max_iter=2000).fit(Zb, yb)
            cl = list(m.classes_); base = cl.index(origin) if origin in cl else None
            out = {}
            for j in leave:
                if j in cl and base is not None:
                    out[j] = m.coef_[cl.index(j)] - m.coef_[base] if len(cl) > 2 else (m.coef_[0] if cl[1] == j else -m.coef_[0])
            return out
        est = fit(Z, y); isos = d.iso3.unique(); boots = {j: [] for j in leave}
        for b in range(300):
            s = rng.choice(isos, len(isos)); idx = np.concatenate([np.where(d.iso3.values == i)[0] for i in s])
            if len(set(y[idx])) < 2: continue
            try: eb = fit(Z[idx], y[idx])
            except Exception: continue
            for j in leave:
                if j in eb: boots[j].append(eb[j])
        for j in leave:
            if j not in est: continue
            Bj = np.array(boots[j])
            for k, c in enumerate(cols):
                rows.append(dict(spec=spec, transition=f"{origin} -> {j}", covariate=c, n_from=len(d), n_moves=int((y == j).sum()),
                                 odds_ratio=np.exp(est[j][k]), or_lo95=np.exp(np.quantile(Bj[:, k], .025)) if len(Bj) > 20 else np.nan,
                                 or_hi95=np.exp(np.quantile(Bj[:, k], .975)) if len(Bj) > 20 else np.nan,
                                 p_boot_beta_gt0=(Bj[:, k] > 0).mean() if len(Bj) > 20 else np.nan))
R = pd.DataFrame(rows); R.round(3).to_csv(OUT / "softmax_transitions_cooking.csv", index=False)
pd.set_option("display.width", 220)
key = R[R.transition.isin(["Stalled -> Converging", "Diverging -> Stalled", "Stalled -> Diverging", "Converging -> Stalled"])]
print(key.round(3).to_string(index=False))
