"""
Rural–urban step 2: convergence rate kappa (gap evolution G_t = G_{t-1} - kappa_c G_{t-1} + eta).
Per-country estimate: annualized  (G_t2 - G_t1)/(t2 - t1) = -kappa_c * G_t1 + e   (no intercept: convergence toward parity)
  - infra series: consecutive annual observations 2000-2024
  - jobs gap (JOIN survey years): consecutive observed survey pairs 2000-2021
Hierarchical (empirical Bayes) partial pooling within region: kappa_c ~ N(mu_r, tau_r^2); normal-normal posterior.
Reports P(kappa_c > 0 | data), posterior mean, half-life ln2/kappa (only when P(kappa>0) >= 0.9), and region summaries.
Rows with |G| < 1pp at start are excluded from slope estimation (no gap to close -> kappa undefined).
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"
P = pd.read_csv(OUT / "rural_urban_panel.csv.gz")
for c in ["fem_nonag_rural", "fem_nonag_urban", "jobs_gap"]: P[c] = P[c] * 100     # shares -> pp
P = P[P.year >= 2000].sort_values(["iso3", "year"])
SERIES = {"infra_gap": "Time-tax infrastructure (composite)", "cooking_gap": "Clean cooking", "water_gap": "Basic water",
          "sanitation_gap": "Basic sanitation", "electricity_gap": "Electricity", "jobs_gap": "Women's non-farm employment"}
reg = P.drop_duplicates("iso3").set_index("iso3")[["country_name", "region_name", "income_level_name"]]

def country_kappa(s):
    rows = []
    for iso, g in P.dropna(subset=[s]).groupby("iso3"):
        g = g[["year", s]].values
        if len(g) < 3: continue
        y0, y1 = g[:-1], g[1:]
        dt = y1[:, 0] - y0[:, 0]; G0 = y0[:, 1]; dG = (y1[:, 1] - y0[:, 1]) / dt
        keep = np.abs(G0) >= 1
        if keep.sum() < 2: continue
        x, y = G0[keep], dG[keep]
        k = -np.sum(x * y) / np.sum(x * x)
        resid = y + k * x; dof = max(len(x) - 1, 1)
        s2 = np.sum(resid ** 2) / dof; se = np.sqrt(max(s2, 1e-8) / np.sum(x * x))
        se = max(se, 0.002)                       # floor: smooth modelled series understate noise
        rows.append(dict(iso3=iso, kappa_hat=k, se=se, n_pairs=int(keep.sum()), gap_first=g[0, 1], gap_last=g[-1, 1],
                         year_first=int(g[0, 0]), year_last=int(g[-1, 0]), resid_sd=np.sqrt(s2)))
    return pd.DataFrame(rows)

allres = []
for s, label in SERIES.items():
    K = country_kappa(s)
    if K.empty: continue
    K = K.join(reg, on="iso3")
    for r, g in K.groupby("region_name"):
        w = 1 / g.se ** 2; mu = np.sum(w * g.kappa_hat) / w.sum()
        tau2 = max(np.var(g.kappa_hat, ddof=1) - np.mean(g.se ** 2), 1e-6) if len(g) > 2 else 1e-4
        pv = 1 / (1 / g.se ** 2 + 1 / tau2); pm = pv * (g.kappa_hat / g.se ** 2 + mu / tau2)
        K.loc[g.index, "kappa_post"] = pm; K.loc[g.index, "kappa_post_sd"] = np.sqrt(pv)
        K.loc[g.index, "region_mu"] = mu; K.loc[g.index, "region_tau"] = np.sqrt(tau2)
    K["p_converging"] = 1 - norm.cdf(0, K.kappa_post, K.kappa_post_sd)
    K["half_life_years"] = np.where(K.p_converging >= 0.9, np.log(2) / K.kappa_post.clip(lower=1e-9), np.nan)
    K["verdict"] = np.select([K.p_converging >= 0.9, K.p_converging <= 0.1], ["converging", "diverging"], "no clear trend")
    K["series"] = s; K["label"] = label; allres.append(K)
R = pd.concat(allres); R.to_csv(OUT / "kappa_by_country.csv", index=False)
summ = R.groupby("label").agg(economies=("iso3", "size"), median_kappa=("kappa_post", "median"),
        share_converging=("verdict", lambda v: (v == "converging").mean()), share_diverging=("verdict", lambda v: (v == "diverging").mean()),
        median_half_life=("half_life_years", "median"), median_gap_last=("gap_last", "median")).round(3)
summ = summ.loc[[v for v in SERIES.values() if v in summ.index]]
print(summ.to_string()); summ.to_csv(OUT / "kappa_summary.csv")
rg = R.pivot_table(index="region_name", columns="label", values="p_converging", aggfunc="median").round(2)
print("\nmedian P(converging) by region:\n", rg[[c for c in SERIES.values() if c in rg.columns]].to_string()); rg.to_csv(OUT / "kappa_region_pconv.csv")
# leakage: countries where infra converging but jobs not
w = R.pivot_table(index="iso3", columns="series", values="p_converging")
both = w.dropna(subset=["infra_gap", "jobs_gap"])
lk = pd.crosstab(np.where(both.infra_gap >= .9, "infra converging", "infra not"), np.where(both.jobs_gap >= .9, "jobs converging", np.where(both.jobs_gap <= .1, "jobs diverging", "jobs no clear trend")))
print("\nleakage table (economies with both):\n", lk.to_string()); lk.to_csv(OUT / "leakage_crosstab.csv")
co = w.dropna(subset=["cooking_gap", "water_gap"]); print("\ncooking vs water: share converging", (co.cooking_gap >= .9).mean().round(2), (co.water_gap >= .9).mean().round(2))
