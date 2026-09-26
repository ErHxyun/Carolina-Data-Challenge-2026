"""Forest plot: each predictor's association with 3-yr gap-closing velocity, alone vs jointly (region+year FE, country-clustered 95% CI)."""
import sys; sys.argv = ["x"]
from pathlib import Path
__file__ = str(Path(__file__).resolve().parent / "predictive_v2_02_predictor_effects.py")
exec(open(__file__).read().split("rows, imp = [], []")[0])
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
cols = [c for c in X_ALL if c != "edu_emp_misalign"]
rows = []
for c in cols:
    dd = prep(3, [c]); r = fit(dd, [c], 3, False); ci = r.conf_int().loc[c]
    rows.append(dict(label=LABEL[c], kind="alone", coef=r.params[c], lo=ci[0], hi=ci[1]))
d = prep(3, cols); r = fit(d, cols, 3, False); ci = r.conf_int()
for c in cols: rows.append(dict(label=LABEL[c], kind="joint", coef=r.params[c], lo=ci.loc[c, 0], hi=ci.loc[c, 1]))
F = pd.DataFrame(rows); F.to_csv(OUT / "forest_alone_vs_joint_3y.csv", index=False)
order = F[F.kind == "alone"].sort_values("coef")["label"].tolist()
y = {l: i for i, l in enumerate(order)}
col = {"alone": "#2a78d6", "joint": "#eb6834"}; off = {"alone": 0.17, "joint": -0.17}
fig, ax = plt.subplots(figsize=(9, 7.5))
ax.axvline(0, color="#8a8a85", lw=1)
for k in ["alone", "joint"]:
    s = F[F.kind == k]
    yy = [y[l] + off[k] for l in s.label]
    ax.hlines(yy, s.lo, s.hi, color=col[k], lw=2)
    ax.plot(s.coef, yy, "o", ms=7, color=col[k], mec="white", mew=1.5,
            label={"alone": "Alone (one predictor + region & year FE)", "joint": "Jointly (all predictors together)"}[k])
ax.set_yticks(range(len(order))); ax.set_yticklabels(order, color="#333333")
ax.set_xlabel("Change in gap-closing velocity per +1 SD of predictor\n(milli-SD per year; median velocity ≈ 5)", color="#333333")
ax.set_title("Which conditions go with women's employment catching up faster?\n3-year velocity, 157–186 economies, 2003–2021, 95% CI clustered by country",
             loc="left", fontsize=11, color="#111111")
ax.grid(axis="x", color="#e6e6e3", lw=0.8); ax.set_axisbelow(True)
for s in ["top", "right", "left"]: ax.spines[s].set_visible(False)
ax.legend(loc="lower right", frameon=False, fontsize=9)
plt.tight_layout(); plt.savefig(OUT / "forest_alone_vs_joint_3y.png", dpi=180)
print("saved")
