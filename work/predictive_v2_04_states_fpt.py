"""
Step 3b — State transitions + regime-switching first passage time (employment gap).
States (non-overlapping 3-year windows starting 2003, 2006, ..., 2021), by velocity v (SD of gap closed per year):
    Closing  : v >  c      Flat : |v| <= c      Widening : v < -c        (main c = 0.005; sensitivity 0.0025, 0.01)
1) Pooled 3x3 transition matrix, country-cluster bootstrap 95% CI, stationary distribution, expected spell length.
2) Covariates of transitions: logit P(next = Closing) and P(next = Widening), given current state + z-scored predictors.
3) First passage: simulate gap paths G_{k+1} = G_k - 3*v_k, state chain from country-specific transition matrix
   (Dirichlet partial pooling toward income-group matrix, 4 pseudo-counts per row), v drawn from the empirical
   distribution of that state within the country's income group. Start: 2024 gap and 2021-24 state.
   Thresholds: (a) halve the 2024 gap, (b) near parity G <= 0.1 SD. Horizon 2099 (25 steps).
Associational / descriptive; not causal.
"""
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm, warnings; warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "predictive_v2"
rng = np.random.default_rng(2026)
P = pd.read_csv(OUT / "panel_v2.csv.gz")
S = ["Closing", "Flat", "Widening"]; IDX = {s: i for i, s in enumerate(S)}
STARTS = list(range(2003, 2022, 3))

def states(c):
    W = P[P.year.isin(STARTS)].dropna(subset=["target_v_employment"]).sort_values(["iso3", "year"]).copy()
    v = W.target_v_employment
    W["state"] = np.select([v > c, v < -c], ["Closing", "Widening"], "Flat")
    W["next_state"] = W.groupby("iso3")["state"].shift(-1)
    W["next_year"] = W.groupby("iso3")["year"].shift(-1)
    return W

def tmat(T):
    M = pd.crosstab(T.state, T.next_state).reindex(index=S, columns=S, fill_value=0)
    return M.div(M.sum(1), axis=0)

def stationary(M):
    w, v = np.linalg.eig(M.values.T); x = np.real(v[:, np.argmin(abs(w - 1))]); return x / x.sum()

res = {}
for c in [0.005, 0.0025, 0.01]:
    W = states(c); T = W[W.next_year == W.year + 3]
    M = tmat(T); res[c] = (W, T, M)
    print(f"\n=== c={c}: {len(T)} transitions, {T.iso3.nunique()} economies; state shares {W.state.value_counts(normalize=True).round(3).to_dict()}")
    print(M.round(3).to_string()); print("stationary:", dict(zip(S, stationary(M).round(3))))

# ---- main spec: bootstrap CI, spell length ----
W, T, M = res[0.005]
isos = T.iso3.unique(); boots = []
for b in range(500):
    samp = rng.choice(isos, len(isos), replace=True)
    Tb = pd.concat([T[T.iso3 == i] for i in samp]); boots.append(tmat(Tb).values)
B = np.array(boots); lo, hi = np.nanpercentile(B, 2.5, 0), np.nanpercentile(B, 97.5, 0)
rows = []
for i, a in enumerate(S):
    for j, b in enumerate(S):
        rows.append(dict(from_state=a, to_state=b, prob=M.values[i, j], ci_lo=lo[i, j], ci_hi=hi[i, j], n_from=int((T.state == a).sum())))
TM = pd.DataFrame(rows); TM.to_csv(OUT / "transition_matrix_main.csv", index=False)
spell = {s: 3 / (1 - M.loc[s, s]) for s in S}
print("\nexpected spell length (years):", {k: round(v, 1) for k, v in spell.items()})
# by income group
inc = T.groupby("income_level_name").apply(lambda g: pd.Series({"n": len(g), "P(stay Widening)": tmat(g).loc["Widening", "Widening"],
        "P(Widening->Closing)": tmat(g).loc["Widening", "Closing"], "P(Closing->Closing)": tmat(g).loc["Closing", "Closing"]})).round(3)
print(inc.to_string()); inc.to_csv(OUT / "transition_by_income.csv")
# 2020 check: transitions into the 2021-24 window
print("\ninto 2021-24 window:\n", tmat(T[T.next_year == 2021]).round(3).to_string())

# ---- covariates of transitions ----
PRED = ["gap_employment_tr", "fertility", "basic_water_rural", "clean_cooking", "log_gdppc_ppp", "gdppc_growth_3y", "fem_agri_emp_share"]
D = T.dropna(subset=PRED).copy()
for cvar in PRED: D[cvar] = (D[cvar] - D[cvar].mean()) / D[cvar].std()
D["cur_Flat"] = (D.state == "Flat").astype(float); D["cur_Widening"] = (D.state == "Widening").astype(float)
cov_rows = []
for target in ["Closing", "Widening"]:
    y = (D.next_state == target).astype(float)
    X = sm.add_constant(D[["cur_Flat", "cur_Widening"] + PRED])
    r = sm.Logit(y, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(D.iso3)[0]})
    ci = r.conf_int()
    for k in X.columns[1:]:
        cov_rows.append(dict(next_state=target, term=k, odds_ratio=np.exp(r.params[k]), or_lo=np.exp(ci.loc[k, 0]), or_hi=np.exp(ci.loc[k, 1]), p=r.pvalues[k], n=int(r.nobs)))
CV = pd.DataFrame(cov_rows); CV.to_csv(OUT / "transition_covariates.csv", index=False)
print("\n", CV.pivot_table(index="term", columns="next_state", values=["odds_ratio", "p"]).round(3).to_string())

# ---- regime-switching first passage ----
Wm = W.copy()
pool_inc = {g: tmat(t) for g, t in T.groupby("income_level_name")}
vdist = {(g, s): t.target_v_employment.values for (g, s), t in Wm.groupby(["income_level_name", "state"])}
vall = {s: t.target_v_employment.values for s, t in Wm.groupby("state")}
last = P[P.year == 2024][["iso3", "country_name", "region_name", "income_level_name", "gap_employment_tr", "gap_employment"]]
cur_state = Wm[Wm.year == 2021].set_index("iso3").state
NS, STEPS = 4000, 25; out = []
for r in last.dropna(subset=["gap_employment_tr"]).itertuples():
    if r.iso3 not in cur_state.index: continue
    g = r.income_level_name if r.income_level_name in pool_inc else None
    prior = pool_inc[g] if g else M
    cnt = pd.crosstab(T[T.iso3 == r.iso3].state, T[T.iso3 == r.iso3].next_state).reindex(index=S, columns=S, fill_value=0)
    Pc = (cnt + 4 * prior).div((cnt + 4 * prior).sum(1), axis=0).values
    G0 = r.gap_employment_tr
    if G0 <= 0.1:
        out.append(dict(iso3=r.iso3, country=r.country_name, region=r.region_name, income=g, gap_2024=G0, start_state=cur_state[r.iso3], status="already near parity")); continue
    half = G0 / 2
    st = np.full(NS, IDX[cur_state[r.iso3]]); G = np.full(NS, G0)
    Th = np.full(NS, np.inf); Tp = np.full(NS, np.inf)
    for k in range(1, STEPS + 1):
        u = rng.random(NS); cum = Pc[st].cumsum(1); st = (u[:, None] > cum).sum(1)
        v = np.empty(NS)
        for s in range(3):
            m = st == s
            pool = vdist.get((g, S[s]), vall[S[s]]); pool = pool if len(pool) >= 15 else vall[S[s]]
            v[m] = rng.choice(pool, m.sum())
        G = G - 3 * v
        yr = 2024 + 3 * k
        Th[np.isinf(Th) & (G <= half)] = yr; Tp[np.isinf(Tp) & (G <= 0.1)] = yr
    q = lambda T_, p: (np.nan if np.isinf(np.quantile(T_, p)) else float(np.quantile(T_, p)))
    out.append(dict(iso3=r.iso3, country=r.country_name, region=r.region_name, income=g, gap_2024=G0, start_state=cur_state[r.iso3],
                    p_halve_by_2030=(Th <= 2030).mean(), p_halve_by_2050=(Th <= 2051).mean(), median_year_halve=q(Th, .5),
                    halve_q10=q(Th, .1), halve_q90=q(Th, .9),
                    p_parity_by_2050=(Tp <= 2051).mean(), p_parity_by_2099=(Tp <= 2099).mean(), median_year_parity=q(Tp, .5),
                    p_widened_2050=np.nan))
F = pd.DataFrame(out)
F["status"] = F["status"].fillna(pd.Series(np.where(F.p_halve_by_2050 >= .5, "likely halves by 2050", "unlikely to halve by 2050"), index=F.index))
F.to_csv(OUT / "first_passage_regime_switching.csv", index=False)
print("\n", F.status.value_counts().to_string())
print(F.dropna(subset=["p_halve_by_2050"]).groupby("region")[["gap_2024", "p_halve_by_2030", "p_halve_by_2050", "p_parity_by_2099", "median_year_halve"]].median().round(2).to_string())
print(F.dropna(subset=["p_halve_by_2050"]).groupby("start_state")[["p_halve_by_2050", "median_year_halve"]].median().round(2).to_string())
