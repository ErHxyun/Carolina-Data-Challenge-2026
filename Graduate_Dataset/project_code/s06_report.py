"""
Step 6 - Country summary table + figures.

  outputs/country_summary.csv    one row per country with every headline metric
  outputs/figures/*.png
"""
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import config as C  # noqa: E402
import latent as L  # noqa: E402
from common import country_table  # noqa: E402

MET, EW, FIG = C.OUT_DIR / "metrics", C.OUT_DIR / "early_warning", C.FIG_DIR
URBAN, RURAL, INK, INK2, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold"})
YEAR = 2021
MIN_GAP = C.MIN_GAP   # below this rural ~ urban and a "delay" is noise


def gap_at(dim, year=YEAR):
    d = L.load(dim)
    isos = sorted(set(d["iso"]))
    G = L.groups(dim, isos)
    return pd.Series(np.nanmedian(G["UW"][:, :, L.yidx(year)] - G["RW"][:, :, L.yidx(year)], 0), index=isos)


def fmt_delay(r):
    if pd.isna(r.delay_median):
        return ""
    if r.delay_is_lower_bound:
        return f">{r.delay_median:.0f}"
    return f"{r.delay_median:.1f} ({r.delay_q05:.1f}-{r.delay_q95:.1f})"


def country_summary():
    ct = country_table()
    dl = pd.read_csv(MET / "opportunity_delay.csv")
    d = dl[dl.year == YEAR]
    out = pd.DataFrame(index=sorted(d.iso.unique()))
    for dim in ["Overall"] + C.TRAJECTORY_DIMS:
        x = d[d.dimension == dim].set_index("iso")
        out[f"gap_{dim}_{YEAR}"] = gap_at(dim).reindex(out.index).round(2)
        out[f"delay_{dim}_{YEAR}"] = x.apply(fmt_delay, axis=1)
        out[f"delay_{dim}_ext_median"] = x.delay_ext_median.round(1)
    pwc = pd.read_csv(MET / "progress_without_convergence.csv")
    for dim in ["Overall", "Health", "Infrastructure", "Education", "Employment"]:
        x = pwc[(pwc.dimension == dim) & (pwc.window == "2010-2020")].set_index("iso")
        out[f"pwc_{dim}_2010_2020"] = x.label
        out[f"p_pwc_{dim}"] = x.p_pwc.round(2)
    hl = pd.read_csv(MET / "inequality_half_life.csv")
    x = hl[hl.dimension == "Overall"].set_index("iso")
    out["p_convergence_Overall"] = x.p_convergence.round(2)
    out["half_life_Overall"] = x.apply(lambda r: "" if pd.isna(r.half_life_median) else
                                       f"{r.half_life_median:.1f} ({r.half_life_q05:.1f}-{r.half_life_q95:.1f})", axis=1)
    out["half_life_verdict"] = x.verdict
    dv = pd.read_csv(MET / "divergence_point.csv")
    for dim in ["Health", "Infrastructure"]:
        x = dv[dv.dimension == dim].set_index("iso")
        out[f"change_point_{dim}"] = x.apply(lambda r: "" if r.type.startswith("No clear") else
                                             f"{r.type.split(' (')[0]} {r.window_start}-{r.window_end} (p={r.p_window:.2f})", axis=1)
    lk = pd.read_csv(MET / "leakage_edu_emp_by_country.csv").set_index("iso")
    out["edu_emp_leakage_Lambda"] = lk.Lambda_median.round(3)
    out["p_edu_emp_leakage"] = lk.p_Lambda_gt_0.round(2)
    ip = pd.read_csv(MET / "intersectional_penalty_by_country.csv").set_index("iso")
    out["intersectional_I"] = ip.I_median.round(3)
    out["p_intersectional_gt0"] = ip.p_I_gt_0.round(2)
    dtw = pd.read_csv(MET / "dtw_analogues.csv").set_index("iso")
    out["dtw_analogues"] = dtw.analogues
    out["share_analogues_escaped"] = dtw.share_analogues_escaped.round(2)
    ewf = sorted(EW.glob("early_warning_*.csv"))
    if ewf:
        ew = pd.read_csv(ewf[-1]).set_index("iso")
        out[f"p_delay_widens_{C.YEAR_END}_{C.YEAR_END + 3}"] = ew.p_widen.round(2)
    out.insert(0, "meaningful_gap", out[f"gap_Overall_{YEAR}"] > MIN_GAP)
    out.insert(0, "region", ct.reindex(out.index).region)
    out.insert(0, "country", ct.reindex(out.index).name)
    out.index.name = "iso"
    out.to_csv(C.OUT_DIR / "country_summary.csv")
    return out


def fig_delay_by_dimension():
    dl = pd.read_csv(MET / "opportunity_delay.csv")
    d = dl[dl.year == YEAR]
    dims = ["Education", "Employment", "Health", "Infrastructure", "Overall"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for k, dim in enumerate(dims):
        x = d[d.dimension == dim]
        unc = x[~x.delay_is_lower_bound & (x.delay_median > 0)].delay_median
        jitter = np.random.default_rng(k).uniform(-0.18, 0.18, len(unc))
        ax.scatter(unc, k + jitter, s=14, color=URBAN, alpha=0.55, lw=0)
        if len(unc):
            ax.plot([unc.median()] * 2, [k - 0.3, k + 0.3], color=INK, lw=2)
        share = x.delay_is_lower_bound.mean()
        ax.text(33, k, f"{share:.0%} beyond record", va="center", fontsize=9, color=INK2)
    ax.set_yticks(range(len(dims)), dims)
    ax.set_xlim(0, 44)
    ax.set_xlabel(f"Opportunity Delay in {YEAR} (years; dots = countries, bar = median)")
    ax.set_title(f"How many years behind urban women are rural women? ({YEAR})", loc="left")
    ax.axvline(31, color=GRID, lw=1, ls="--")
    fig.tight_layout(); fig.savefig(FIG / "fig1_delay_by_dimension.png", dpi=160); plt.close(fig)


def fig_trajectories(isos=("IND", "BGD", "KEN", "ETH", "PER", "VNM")):
    isos = [i for i in isos if i in set(L.load("Overall")["iso"])]
    G = L.groups("Overall", isos)
    yrs = L.years()
    names = country_table().reindex(isos).name.values
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.4), sharex=True, sharey=True)
    for ax, i, nm in zip(axes.flat, range(len(isos)), names):
        for g, col, lab in (("UW", URBAN, "Urban women"), ("RW", RURAL, "Rural women")):
            q = np.nanquantile(G[g][:, i], [0.05, 0.5, 0.95], axis=0)
            ax.fill_between(yrs, q[0], q[2], color=col, alpha=0.18, lw=0)
            ax.plot(yrs, q[1], color=col, lw=2, label=lab)
        ax.set_title(nm, loc="left")
    axes.flat[0].legend(frameon=False, loc="upper left")
    fig.supylabel("Latent opportunity (posterior median, 90% band)", color=INK2, fontsize=10)
    fig.suptitle("Two women, same country, different development decades", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "fig2_trajectories.png", dpi=160); plt.close(fig)


def fig_delay_ranking(n=30):
    dl = pd.read_csv(MET / "opportunity_delay.csv")
    d = dl[(dl.year == YEAR) & (dl.dimension == "Overall") & ~dl.delay_is_lower_bound & (dl.delay_median > 0)]
    d = d[d.iso.map(gap_at("Overall")) > MIN_GAP]
    d = d.sort_values("delay_median").tail(n)
    names = country_table().reindex(d.iso).name.values
    fig, ax = plt.subplots(figsize=(7, 0.24 * len(d) + 1.5))
    y = np.arange(len(d))
    ax.hlines(y, d.delay_q05, d.delay_q95, color=URBAN, alpha=0.4, lw=3)
    ax.scatter(d.delay_median, y, color=URBAN, s=30, zorder=3)
    ax.set_yticks(y, names, fontsize=8)
    ax.set_xlabel("Opportunity Delay, years (median, 90% credible interval)")
    ax.set_title(f"Largest measurable delays, overall index ({YEAR})", loc="left", pad=18)
    ax.text(0, 1.005, "Countries with a meaningful gap; delays beyond the 1990 record not shown",
            transform=ax.transAxes, fontsize=8.5, color=INK2, va="bottom")
    fig.tight_layout(); fig.savefig(FIG / "fig3_delay_ranking.png", dpi=160); plt.close(fig)


def fig_pwc():
    p = pd.read_csv(MET / "progress_without_convergence.csv")
    p = p[(p.dimension == "Overall") & (p.window == "2010-2020")]
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    col = np.where(p.label == "Progress Without Convergence", RURAL, np.where(p.label == "Converging progress", URBAN, "#a3a29c"))
    ax.scatter(p.dZ_rural_median, p.dGap_median, c=col, s=22, lw=0, alpha=0.85)
    ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
    ax.text(0.98, 0.97, "Progress Without Convergence\n(rural women improve, gap widens)", transform=ax.transAxes,
            ha="right", va="top", fontsize=9, color=INK)
    ax.text(0.02, 0.03, "Converging progress (blue)\ngrey = uncertain / no rural progress", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=9, color=INK)
    names = country_table().name
    top = p[p.label == "Progress Without Convergence"].nlargest(5, "dGap_median").sort_values("dGap_median")
    for k, (_, r) in enumerate(top.iterrows()):
        ax.annotate(names.get(r.iso, r.iso), (r.dZ_rural_median, r.dGap_median), fontsize=8, color=INK2,
                    xytext=(6, -8 if k % 2 else 4), textcoords="offset points")
    ax.set_xlabel("Change in rural women's opportunity, 2010-2020")
    ax.set_ylabel("Change in urban-rural gap, 2010-2020")
    ax.set_title("Progress is not the same as convergence", loc="left")
    fig.tight_layout(); fig.savefig(FIG / "fig4_progress_without_convergence.png", dpi=160); plt.close(fig)


def fig_leakage():
    lk = pd.read_csv(MET / "progress_leakage.csv")
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    y = np.arange(len(lk))[::-1]
    ax.hlines(y, lk.Lambda_q05, lk.Lambda_q95, color=URBAN, lw=3, alpha=0.45)
    ax.scatter(lk.Lambda_median, y, color=URBAN, s=36, zorder=3)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(y, [l.split(",")[0] for l in lk.link], fontsize=8.5)
    for yy, p in zip(y, lk.p_Lambda_gt_0):
        ax.text(ax.get_xlim()[1], yy, f"  P(Λ>0)={p:.2f}", va="center", fontsize=8.5, color=INK2)
    ax.set_xlabel("Λ = urban-women slope − rural-women slope  (> 0: weaker conversion for rural women)")
    ax.set_title("Progress Leakage along the opportunity pathway", loc="left")
    fig.tight_layout(); fig.savefig(FIG / "fig5_progress_leakage.png", dpi=160); plt.close(fig)


def fig_early_warning():
    from sklearn.metrics import roc_curve
    pr = pd.read_csv(EW / "ew_test_predictions.csv")
    perf = pd.read_csv(EW / "ew_performance.csv").set_index("model")
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    for col, name, c in (("p_lgbm", "LightGBM", URBAN), ("p_logit", "Elastic-net logistic", RURAL)):
        f, t, _ = roc_curve(pr.y, pr[col])
        ax.plot(f, t, color=c, lw=2, label=f"{name} (AUC {perf.loc[name, 'auc']:.2f})")
    ax.plot([0, 1], [0, 1], color=GRID, lw=1, ls="--")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("Early warning: will the delay widen in 3 years?\n(test years 2016-2021)", loc="left")
    ax.legend(frameon=False, loc="lower right", fontsize=8.5)
    fig.tight_layout(); fig.savefig(FIG / "fig6_early_warning_roc.png", dpi=160); plt.close(fig)


def fig_escapers():
    f = MET / "escaper_characteristics.csv"
    if not f.exists():
        return
    e = pd.read_csv(f, index_col=0).head(10)[::-1]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    col = np.where(e.shap_direction > 0, URBAN, RURAL)
    ax.set_axisbelow(True)
    ax.barh(range(len(e)), e.shap_mean_abs, color=col, height=0.6)
    ax.set_yticks(range(len(e)), e.index, fontsize=8.5)
    ax.set_xlabel("Mean |SHAP| (blue = higher value -> more likely to escape; orange = less likely)")
    ax.set_title("What distinguished historical Escapers (associational)", loc="left")
    fig.tight_layout(); fig.savefig(FIG / "fig7_escaper_characteristics.png", dpi=160); plt.close(fig)


def main():
    s = country_summary()
    for f in (fig_delay_by_dimension, fig_trajectories, fig_delay_ranking, fig_pwc, fig_leakage,
              fig_early_warning, fig_escapers):
        f()
    print(f"country_summary.csv: {len(s)} countries; figures -> {FIG}")


if __name__ == "__main__":
    main()
