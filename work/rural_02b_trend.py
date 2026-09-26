"""
Rural–urban step 2b: bias-robust convergence test.
The kappa regression (dG on G_{t-1}) is biased toward 'convergence' when G is measured with noise (regression to the mean),
which matters for survey-based JOIN data. Here: per-country linear trend of the gap on calendar year (regressor has no error),
pooled residual variance by series, empirical-Bayes shrinkage within region -> P(gap shrinking | data).
Also flags 'Progress without convergence' (rural level rising AND gap widening) for each infrastructure item.
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"
P = pd.read_csv(OUT / "rural_urban_panel.csv.gz")
for c in ["fem_nonag_rural", "fem_nonag_urban", "jobs_gap"]: P[c] = P[c] * 100
P = P[P.year >= 2000]
SERIES = {"infra_gap": ("infra_rural", "Time-tax infrastructure (composite)"), "cooking_gap": ("cooking_rural", "Clean cooking"),
          "water_gap": ("water_rural", "Basic water"), "sanitation_gap": ("sanitation_rural", "Basic sanitation"),
          "electricity_gap": ("electricity_rural", "Electricity"), "jobs_gap": ("fem_nonag_rural", "Women's non-farm employment")}
reg = P.drop_duplicates("iso3").set_index("iso3")[["country_name", "region_name", "income_level_name"]]
out = []
for s, (rur, label) in SERIES.items():
    rows = []
    for iso, g in P.dropna(subset=[s]).groupby("iso3"):
        if len(g) < 3 or g.year.max() - g.year.min() < 5: continue
        t = g.year.values - g.year.mean(); b = np.sum(t * g[s].values) / np.sum(t * t)
        rt = g.dropna(subset=[rur]); br = np.polyfit(rt.year, rt[rur], 1)[0] if len(rt) >= 3 else np.nan
        res = g[s].values - g[s].mean() - b * t
        rows.append(dict(iso3=iso, slope=b, sxx=np.sum(t * t), ssr=np.sum(res ** 2), n=len(g), rural_slope=br,
                         gap_first=g[s].iloc[0], gap_last=g[s].iloc[-1], y0=int(g.year.min()), y1=int(g.year.max())))
    K = pd.DataFrame(rows).join(reg, on="iso3")
    s2 = K.ssr.sum() / max((K.n - 2).sum(), 1)            # pooled residual variance
    K["se"] = np.sqrt(np.maximum(K.ssr / np.maximum(K.n - 2, 1), s2 * 0.25) / K.sxx)   # own, floored at 1/4 pooled
    for r, g in K.groupby("region_name"):
        w = 1 / g.se ** 2; mu = np.sum(w * g.slope) / w.sum(); tau2 = max(np.var(g.slope, ddof=1) - np.mean(g.se ** 2), 1e-4) if len(g) > 2 else 0.05
        pv = 1 / (1 / g.se ** 2 + 1 / tau2); K.loc[g.index, "slope_post"] = pv * (g.slope / g.se ** 2 + mu / tau2); K.loc[g.index, "slope_post_sd"] = np.sqrt(pv)
    K["p_shrinking"] = norm.cdf(0, K.slope_post, K.slope_post_sd)
    K["verdict"] = np.select([K.p_shrinking >= .9, K.p_shrinking <= .1], ["gap shrinking", "gap widening"], "no clear trend")
    K["progress_without_convergence"] = (K.rural_slope > 0) & (K.verdict == "gap widening")
    K["series"] = s; K["label"] = label; out.append(K)
R = pd.concat(out); R.to_csv(OUT / "gap_trend_by_country.csv", index=False)
S = R.groupby("label").agg(economies=("iso3", "size"), median_slope_pp_per_yr=("slope_post", "median"),
      share_shrinking=("verdict", lambda v: (v == "gap shrinking").mean()), share_widening=("verdict", lambda v: (v == "gap widening").mean()),
      share_progress_without_convergence=("progress_without_convergence", "mean"), median_gap_last=("gap_last", "median")).round(3)
S = S.loc[[v[1] for v in SERIES.values() if v[1] in S.index]]; print(S.to_string()); S.to_csv(OUT / "gap_trend_summary.csv")
print("\nregion x series share widening:\n", R.pivot_table(index="region_name", columns="label", values="verdict", aggfunc=lambda v: (v == "gap widening").mean()).round(2).to_string())
pw = R[(R.series == "cooking_gap") & R.progress_without_convergence]
print(f"\nclean cooking: progress without convergence in {len(pw)} economies; by region:\n", pw.region_name.value_counts().to_string())
print(pw.sort_values("slope_post", ascending=False)[["country_name", "gap_first", "gap_last", "y0", "y1", "slope_post", "rural_slope"]].head(15).round(2).to_string(index=False))
