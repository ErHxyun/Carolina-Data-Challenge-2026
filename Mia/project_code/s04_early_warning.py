"""
Step 4 - PREDICT: one early-warning model.

  Y_{c,t} = 1( D_{c,t+3} > D_{c,t} )  -- will rural women's Opportunity Delay widen over the next 3 years?

Features are the statistical discoveries themselves, built only from information
available at time t (filtered latent states, not smoothed ones):
  delay D_t and its 3-year change, overall and per-dimension gaps G_t and their changes,
  rural women's levels, a rolling Education->Employment conversion gap (leakage proxy),
  and national macro controls.

The label uses the full-data posterior: Y = 1 if P(D_{t+3} > D_t | data) > 0.5.

Validation is chronological with an embargo so no label overlaps the next block:
  train  t <= 2010                (labels <= 2013)
  valid  2013 <= t <= 2015        (hyper-parameters chosen here)
  test   2016 <= t <= 2021        (final model refit on t <= 2013)
plus leave-one-region-out CV on t <= 2015.

Models: persistence baseline, elastic-net logistic regression, LightGBM (+ SHAP).
"""
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import lightgbm as lgb

import config as C
import latent as L
from common import region_of
from s03_metrics import MET, base_features, eligible, opportunity_delay

warnings.filterwarnings("ignore")
EW = C.OUT_DIR / "early_warning"
EW.mkdir(exist_ok=True)
H = 3
MIN_GAP = C.MIN_GAP
TRAIN_END, VAL, TEST = 2010, (2013, 2015), (2016, C.YEAR_END - H)


def build_dataset():
    isos = eligible("Overall")
    dd = np.load(MET / "delay_draws_overall.npz")
    D, cens, iso_d = dd["Dext"], dd["cens"], list(dd["iso"])
    # delay from filtered states (what an analyst would have seen at time t)
    Gf = L.groups("Overall", iso_d, filtered=True)
    _, cf, Df = opportunity_delay(Gf["RW"][None], Gf["UW"][None])
    Df, cf = Df[0], cf[0]
    rows = []
    for c, iso in enumerate(iso_d):
        for t in range(L.yidx(2003), len(C.YEARS)):
            y = np.nan
            if t + H < len(C.YEARS) and np.isfinite(D[:, c, t]).all():
                y = float((D[:, c, t + H] > D[:, c, t]).mean() > 0.5)
            rows.append(dict(iso=iso, year=C.YEARS[t], y=y, delay_f=Df[c, t],
                             ddelay3_f=Df[c, t] - Df[c, t - 3], delay_censored_f=float(cf[c, t])))
    df = pd.DataFrame(rows)
    feats = base_features(df[["iso", "year"]], filtered=True)
    df = df.merge(feats, on=["iso", "year"])
    df["region"] = region_of(df.iso.values)
    return df


def metrics(y, p):
    return dict(n=len(y), pos_rate=float(np.mean(y)), auc=roc_auc_score(y, p),
                pr_auc=average_precision_score(y, p), brier=brier_score_loss(y, p))


def main():
    df = build_dataset()
    # a delay is only meaningful where a real rural-urban gap exists (drop near-parity settings)
    df = df[df.gap_Overall > MIN_GAP]
    df.to_csv(EW / "ew_dataset.csv", index=False)
    feat_cols = [c for c in df.columns if c not in ("iso", "year", "y", "region")]
    lab = df.dropna(subset=["y"])
    tr = lab[lab.year <= TRAIN_END]
    va = lab[lab.year.between(*VAL)]
    te = lab[lab.year.between(*TEST)]
    refit = lab[lab.year <= VAL[0]]
    print(f"rows: train={len(tr)} valid={len(va)} test={len(te)}  positives(test)={te.y.mean():.2f}")

    def logit_model(cval, l1):
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(penalty="elasticnet", solver="saga", C=cval, l1_ratio=l1, max_iter=5000))

    def gbm_model(nl, lr, n):
        return lgb.LGBMClassifier(num_leaves=nl, learning_rate=lr, n_estimators=n, min_child_samples=20,
                                  subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                                  verbose=-1, random_state=C.SEED)

    # --- tune on the validation block
    best_lr = max(((c, l) for c in (0.01, 0.05, 0.2, 1.0) for l in (0.0, 0.5, 1.0)),
                  key=lambda a: roc_auc_score(va.y, logit_model(*a).fit(tr[feat_cols], tr.y).predict_proba(va[feat_cols])[:, 1]))
    best_gb = max(((nl, lr, n) for nl in (4, 8, 16) for lr in (0.03, 0.1) for n in (100, 300)),
                  key=lambda a: roc_auc_score(va.y, gbm_model(*a).fit(tr[feat_cols], tr.y).predict_proba(va[feat_cols])[:, 1]))
    print("chosen logistic (C, l1_ratio):", best_lr, " lightgbm (leaves, lr, trees):", best_gb)

    # --- refit on train+valid (embargoed) and evaluate on the test block
    res, preds = [], te[["iso", "year", "y"]].copy()
    persistence = (te.ddelay3_f > 0).astype(float) * 0.8 + 0.1
    res.append(dict(model="Persistence (delay rose last 3y)", **metrics(te.y, persistence)))
    m_lr = logit_model(*best_lr).fit(refit[feat_cols], refit.y)
    preds["p_logit"] = m_lr.predict_proba(te[feat_cols])[:, 1]
    res.append(dict(model="Elastic-net logistic", **metrics(te.y, preds.p_logit)))
    m_gb = gbm_model(*best_gb).fit(refit[feat_cols], refit.y)
    preds["p_lgbm"] = m_gb.predict_proba(te[feat_cols])[:, 1]
    res.append(dict(model="LightGBM", **metrics(te.y, preds.p_lgbm)))

    # --- leave-one-region-out on t <= VAL end
    pool = lab[lab.year <= VAL[1]]
    for name, mk in [("Elastic-net logistic", lambda: logit_model(*best_lr)), ("LightGBM", lambda: gbm_model(*best_gb))]:
        ys, ps = [], []
        for r in pool.region.unique():
            trn, tst = pool[pool.region != r], pool[pool.region == r]
            if tst.y.nunique() < 2:
                continue
            ps.append(mk().fit(trn[feat_cols], trn.y).predict_proba(tst[feat_cols])[:, 1]); ys.append(tst.y.values)
        res.append(dict(model=f"{name} [leave-region-out]", **metrics(np.concatenate(ys), np.concatenate(ps))))
    res = pd.DataFrame(res)
    res.to_csv(EW / "ew_performance.csv", index=False)
    preds.to_csv(EW / "ew_test_predictions.csv", index=False)
    print(res.round(3).to_string(index=False))

    # --- interpretation
    coefs = pd.Series(m_lr[-1].coef_[0], index=feat_cols).sort_values(key=np.abs, ascending=False)
    coefs.to_csv(EW / "ew_logit_coefficients.csv", header=["coef_std"])
    try:
        import shap
        Xte = te[feat_cols]
        sv = shap.TreeExplainer(m_gb).shap_values(Xte)
        sv = sv[1] if isinstance(sv, list) else sv
        imp = pd.Series(np.abs(sv).mean(0), index=feat_cols).sort_values(ascending=False)
    except Exception:
        imp = pd.Series(m_gb.feature_importances_, index=feat_cols, dtype=float).sort_values(ascending=False)
    imp.to_csv(EW / "ew_shap_importance.csv", header=["mean_abs_shap"])

    # --- the actual early warning: latest year, final models refit on all labelled rows
    final_lr = logit_model(*best_lr).fit(lab[feat_cols], lab.y)
    final_gb = gbm_model(*best_gb).fit(lab[feat_cols], lab.y)
    latest = df[df.year == C.YEAR_END].copy()
    latest["p_widen_logit"] = final_lr.predict_proba(latest[feat_cols])[:, 1]
    latest["p_widen_lgbm"] = final_gb.predict_proba(latest[feat_cols])[:, 1]
    latest["p_widen"] = latest[["p_widen_logit", "p_widen_lgbm"]].mean(1)
    latest = latest.sort_values("p_widen", ascending=False)
    latest[["iso", "year", "region", "delay_f", "ddelay3_f", "gap_Overall", "p_widen_logit", "p_widen_lgbm", "p_widen"]] \
        .to_csv(EW / f"early_warning_{C.YEAR_END}_to_{C.YEAR_END + H}.csv", index=False)
    print(f"\nTop early-warning countries ({C.YEAR_END} -> {C.YEAR_END + H}):")
    print(latest[["iso", "delay_f", "p_widen"]].head(10).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
