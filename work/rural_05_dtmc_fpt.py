"""
Rural–urban step 5: analytic first-passage times via first-step analysis (Kulkarni, Modeling & Analysis of Stochastic Systems, Ch. 3).
Let T = min{n >= 0 : X_n in A}. With B = P restricted to the non-target states:
    P(T > n | X_0 = i) = (B^n e)_i          (Thm 3.1)
    m_i = E[T | X_0 = i] = ((I - B)^{-1} e)_i   (Thm 3.3, when target is reached w.p. 1)
    u_i = P(T < inf | X_0 = i) via the absorption equations (Sec 3.3)
(1) Regime chain (HMM, clean-cooking gap, annual steps): T = first year in the 'Converging' regime,
    initial distribution a = country's filtered regime probabilities in its latest year.
(2) Gap-level chain: urban-rural gap discretised into bins; 'near parity (<=2pp)' made absorbing; annual transition
    matrix estimated from pooled 2000-2023 country-year transitions; expected years to parity and P(parity by 2050) by bin.
"""
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"

def fpt_stats(P, target, a=None, horizons=(6, 26)):
    idx = [i for i in range(len(P)) if i not in target]
    B = P[np.ix_(idx, idx)]; e = np.ones(len(idx))
    try: m = np.linalg.solve(np.eye(len(idx)) - B, e)
    except np.linalg.LinAlgError: m = np.full(len(idx), np.inf)
    surv = {h: np.linalg.matrix_power(B, h) @ e for h in horizons}
    return idx, m, surv

# (1) regime chain for clean cooking
A = pd.read_csv(OUT / "hmm_cooking_gap_transitions.csv", index_col=0)
LAB = list(A.index); Pm = A.values
idx, m, surv = fpt_stats(Pm, target=[LAB.index("Converging")])
print("Regime chain (clean cooking, annual):")
for k, i in enumerate(idx): print(f"  from {LAB[i]:10s}: E[T to Converging] = {m[k]:.1f} yrs; P(reach by 2030) = {1-surv[6][k]:.2f}; by 2050 = {1-surv[26][k]:.2f}")
L = pd.read_csv(OUT / "hmm_cooking_gap_latest.csv")
a = L[["p_stall", "p_div"]].values; pc = L["p_conv"].values
# country-level: P(T <= h) = a_conv + sum_i a_i (1 - v_i(h)); E[T] = sum a_i m_i
L["E_years_to_converging"] = a @ m
L["P_converging_regime_by_2030"] = pc + a @ (1 - surv[6]); L["P_converging_regime_by_2050"] = pc + a @ (1 - surv[26])
L.to_csv(OUT / "dtmc_regime_fpt_cooking.csv", index=False)
print(L.groupby("region_name")[["P_converging_regime_by_2030", "P_converging_regime_by_2050", "E_years_to_converging"]].median().round(2).to_string())

# (2) gap-level absorbing chain
P = pd.read_csv(OUT / "rural_urban_panel.csv.gz").sort_values(["iso3", "year"])
bins = [-np.inf, 2, 5, 10, 20, 35, 50, np.inf]; names = ["<=2 (parity)", "2-5", "5-10", "10-20", "20-35", "35-50", ">50"]
rows = []
for s in ["infra_gap", "cooking_gap", "water_gap", "sanitation_gap"]:
    D = P[P.year.between(2000, 2024)].dropna(subset=[s]).copy()
    D["b"] = pd.cut(D[s], bins, labels=False); D["b_next"] = D.groupby("iso3").b.shift(-1)
    D["y_next"] = D.groupby("iso3").year.shift(-1); T = D[D.y_next == D.year + 1]
    C = pd.crosstab(T.b, T.b_next).reindex(index=range(7), columns=range(7), fill_value=0).values.astype(float)
    C[0] = 0; C[0, 0] = 1                                   # parity absorbing
    Pg = C / C.sum(1, keepdims=True)
    idx, m, surv = fpt_stats(Pg, target=[0], horizons=(6, 26, 76))
    cur = D[D.year == D.groupby("iso3").year.transform("max")].b.value_counts().reindex(range(7), fill_value=0)
    for k, i in enumerate(idx):
        rows.append(dict(series=s, from_bin=names[i], E_years_to_parity=m[k], P_parity_by_2030=1 - surv[6][k], P_parity_by_2050=1 - surv[26][k],
                         P_parity_by_2100=1 - surv[76][k], n_transitions_from_bin=int(C[i].sum()), economies_in_bin_now=int(cur[i])))
G = pd.DataFrame(rows); G.to_csv(OUT / "dtmc_gap_level_fpt.csv", index=False)
print("\nGap-level absorbing chain (annual; parity = gap <= 2pp absorbing):")
print(G.pivot_table(index="from_bin", columns="series", values="E_years_to_parity").reindex(names[1:]).round(0).to_string())
print(G.pivot_table(index="from_bin", columns="series", values="P_parity_by_2050").reindex(names[1:]).round(2).to_string())
print(G.pivot_table(index="from_bin", columns="series", values="economies_in_bin_now").reindex(names[1:]).to_string())
