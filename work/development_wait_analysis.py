from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pycountry
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "outputs" / "world_bank_sources"
OUT = ROOT / "outputs" / "development_wait_analysis"
OUT.mkdir(parents=True, exist_ok=True)

REAL_ISO3 = {c.alpha_3 for c in pycountry.countries} | {"XKX"}
START_YEAR = 2000
END_YEAR = 2024
HORIZON = 3
RNG = np.random.default_rng(20260926)


SOURCE_DIRS = {
    2: DATA_ROOT / "002_WDI",
    12: DATA_ROOT / "012_EDS",
    14: DATA_ROOT / "014_GDS",
    16: DATA_ROOT / "016_HNP",
    86: DATA_ROOT / "086_JON",
}


OUTCOME_SPECS = {
    # code: (short name, direction, domain, sex)
    "SE.SEC.ENRR.FE": ("secondary_enrollment", 1, "education", "female"),
    "SE.SEC.ENRR.MA": ("secondary_enrollment", 1, "education", "male"),
    "SL.TLF.CACT.FE.ZS": ("labor_participation", 1, "employment", "female"),
    "SL.TLF.CACT.MA.ZS": ("labor_participation", 1, "employment", "male"),
    "SL.EMP.TOTL.SP.FE.ZS": ("employment_ratio", 1, "employment", "female"),
    "SL.EMP.TOTL.SP.MA.ZS": ("employment_ratio", 1, "employment", "male"),
    "SL.EMP.VULN.FE.ZS": ("secure_employment", -1, "employment", "female"),
    "SL.EMP.VULN.MA.ZS": ("secure_employment", -1, "employment", "male"),
    "SL.UEM.TOTL.FE.ZS": ("inverse_unemployment", -1, "employment", "female"),
    "SL.UEM.TOTL.MA.ZS": ("inverse_unemployment", -1, "employment", "male"),
}


PREDICTOR_SPECS = {
    "SP.RUR.TOTL.ZS": "rural_population_pct",
    "EG.ELC.ACCS.RU.ZS": "rural_electricity_pct",
    "NY.GDP.PCAP.PP.KD": "gdp_per_capita_ppp",
    "GOV_WGI_GE_EST": "government_effectiveness",
    "SP.DYN.TFRT.IN": "fertility_rate",
    "IT.NET.USER.ZS": "internet_total_pct",
    "IQ.SPI.OVRL": "statistical_performance",
}


SPARSE_SPECS = {
    "SG.TIM.UWRK.FE": "unpaid_work_female_pct_day",
    "SG.TIM.UWRK.MA": "unpaid_work_male_pct_day",
    "account.t.d.1": "account_female_pct",
    "account.t.d.2": "account_male_pct",
    "ID.OWN.TOTL.FE.ZS": "id_ownership_female_pct",
    "IT.NET.USER.FE.ZS": "internet_female_pct",
    "IT.NET.USER.MA.ZS": "internet_male_pct",
}


def indicator_path(code: str) -> Path:
    """Prefer WDI for duplicated indicators, then the specialist sources."""
    for sid in (2, 14, 12, 16, 86):
        path = SOURCE_DIRS[sid] / f"{code}.csv.gz"
        if path.exists():
            return path
    raise FileNotFoundError(code)


def load_indicator(code: str, name: str) -> pd.DataFrame:
    df = pd.read_csv(indicator_path(code), usecols=["country", "iso3", "date", "value"])
    df["year"] = pd.to_numeric(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[
        df["iso3"].isin(REAL_ISO3)
        & df["year"].between(START_YEAR, END_YEAR)
        & df["value"].notna()
    ].copy()
    df["year"] = df["year"].astype(int)
    return df[["country", "iso3", "year", "value"]].rename(columns={"value": name})


def outer_merge(frames: list[pd.DataFrame]) -> pd.DataFrame:
    out = frames[0]
    for frame in frames[1:]:
        out = out.merge(frame, on=["country", "iso3", "year"], how="outer")
    return out.sort_values(["iso3", "year"]).reset_index(drop=True)


def build_outcome_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    coverage = []
    for code, (metric, direction, domain, sex) in OUTCOME_SPECS.items():
        raw = load_indicator(code, "raw_value")
        raw["metric"] = metric
        raw["domain"] = domain
        raw["sex"] = sex
        raw["direction"] = direction
        raw["oriented_value"] = direction * raw["raw_value"]
        rows.append(raw)
        by_country = raw.groupby("iso3")["year"].nunique()
        coverage.append(
            {
                "code": code,
                "metric": metric,
                "domain": domain,
                "sex": sex,
                "rows": len(raw),
                "countries": raw["iso3"].nunique(),
                "first_year": raw["year"].min(),
                "last_year": raw["year"].max(),
                "median_country_years": float(by_country.median()),
            }
        )
    long = pd.concat(rows, ignore_index=True)

    # Use fixed pooled scaling over 2000-2016 so future information does not define the scale.
    train = long[long["year"] <= 2016]
    scaling = (
        train.groupby("metric")["oriented_value"]
        .agg(["mean", "std"])
        .replace({"std": {0: np.nan}})
    )
    long = long.join(scaling, on="metric")
    long["z"] = (long["oriented_value"] - long["mean"]) / long["std"]
    return long, pd.DataFrame(coverage)


def interpolate_short_gaps(series: pd.Series, limit: int = 2) -> pd.Series:
    return series.interpolate(limit=limit, limit_area="inside")


def build_scores(long: pd.DataFrame) -> pd.DataFrame:
    grid = pd.MultiIndex.from_product(
        [sorted(long["iso3"].unique()), range(START_YEAR, END_YEAR + 1), ["female", "male"]],
        names=["iso3", "year", "sex"],
    ).to_frame(index=False)
    names = long[["iso3", "country"]].drop_duplicates("iso3")
    grid = grid.merge(names, on="iso3", how="left")
    metric = (
        long.pivot_table(
            index=["iso3", "country", "year", "sex"],
            columns="metric",
            values="z",
            aggfunc="first",
        )
        .reset_index()
    )
    panel = grid.merge(metric, on=["iso3", "country", "year", "sex"], how="left")
    metric_cols = sorted({spec[0] for spec in OUTCOME_SPECS.values()})
    for col in metric_cols:
        panel[col] = panel.groupby(["iso3", "sex"], group_keys=False)[col].apply(interpolate_short_gaps)

    employment_cols = [
        "labor_participation",
        "employment_ratio",
        "secure_employment",
        "inverse_unemployment",
    ]
    panel["education_score"] = panel["secondary_enrollment"]
    panel["employment_n"] = panel[employment_cols].notna().sum(axis=1)
    panel["employment_score"] = panel[employment_cols].mean(axis=1)
    panel.loc[panel["employment_n"] < 3, "employment_score"] = np.nan
    panel["joint_n"] = panel[["education_score", "employment_score"]].notna().sum(axis=1)
    panel["joint_score"] = panel[["education_score", "employment_score"]].mean(axis=1)
    panel.loc[panel["joint_n"] < 2, "joint_score"] = np.nan

    # Three-year centered smoothing reduces single-survey-year jumps.
    for col in ["education_score", "employment_score", "joint_score"]:
        panel[f"{col}_smooth"] = panel.groupby(["iso3", "sex"], group_keys=False)[col].apply(
            lambda x: x.rolling(3, center=True, min_periods=2).mean()
        )
    return panel


def compute_delay_for_domain(scores: pd.DataFrame, score_col: str, label: str) -> pd.DataFrame:
    out = []
    for iso3, country in scores.groupby("iso3"):
        female = country[country["sex"] == "female"].set_index("year")[score_col]
        male = country[country["sex"] == "male"].set_index("year")[score_col]
        years = np.arange(START_YEAR, END_YEAR + 1)
        male_vals = male.reindex(years).to_numpy(dtype=float)
        valid_m = np.isfinite(male_vals)
        if valid_m.sum() < 10:
            continue
        iso = IsotonicRegression(increasing=True, out_of_bounds="clip")
        male_fit = np.full_like(male_vals, np.nan)
        male_fit[valid_m] = iso.fit_transform(years[valid_m], male_vals[valid_m])
        # Interpolate fitted reference over internal missing years.
        male_fit = pd.Series(male_fit, index=years).interpolate(limit_area="inside").to_numpy()
        for year in years:
            fv = female.get(year, np.nan)
            eligible = (years <= year) & np.isfinite(male_fit)
            if not np.isfinite(fv) or eligible.sum() < 5:
                continue
            ey = years[eligible]
            ev = male_fit[eligible]
            if fv >= ev[-1]:
                matched = year
                delay = 0.0
                censored = False
            elif fv < ev[0]:
                matched = int(ey[0])
                delay = float(year - matched)
                censored = True
            else:
                idx = int(np.argmin(np.abs(ev - fv)))
                matched = int(ey[idx])
                delay = float(year - matched)
                censored = False
            out.append(
                {
                    "iso3": iso3,
                    "country": country["country"].dropna().iloc[0],
                    "year": int(year),
                    "domain": label,
                    "female_score": float(fv),
                    "matched_reference_year": matched,
                    "delay_years": delay,
                    "left_censored": censored,
                    "match_abs_error": float(np.min(np.abs(ev - fv))),
                }
            )
    return pd.DataFrame(out)


def bootstrap_latest_delay(scores: pd.DataFrame, long: pd.DataFrame, n_draws: int = 200) -> pd.DataFrame:
    """Indicator-resampling uncertainty for latest joint delay; not a Bayesian posterior."""
    results = []
    metrics = sorted(long["metric"].unique())
    latest_year = int(scores["year"].max())
    base = scores[["iso3", "country", "year", "sex"]].copy()
    wide = long.pivot_table(index=["iso3", "country", "year", "sex"], columns="metric", values="z").reset_index()
    for draw in range(n_draws):
        chosen = RNG.choice(metrics, size=len(metrics), replace=True)
        draw_panel = base.merge(wide, on=["iso3", "country", "year", "sex"], how="left")
        vals = pd.concat([draw_panel[m] for m in chosen], axis=1)
        draw_panel["boot_score"] = vals.mean(axis=1)
        draw_panel.loc[vals.notna().sum(axis=1) < 3, "boot_score"] = np.nan
        draw_panel["boot_score"] = draw_panel.groupby(["iso3", "sex"], group_keys=False)["boot_score"].apply(
            lambda x: x.interpolate(limit=2, limit_area="inside").rolling(3, center=True, min_periods=2).mean()
        )
        d = compute_delay_for_domain(draw_panel, "boot_score", "joint")
        d = d[d["year"] == latest_year][["iso3", "delay_years"]]
        d["draw"] = draw
        results.append(d)
    if not results:
        return pd.DataFrame()
    draws = pd.concat(results, ignore_index=True)
    return (
        draws.groupby("iso3")["delay_years"]
        .agg(
            delay_boot_median="median",
            delay_p05=lambda x: x.quantile(0.05),
            delay_p95=lambda x: x.quantile(0.95),
            bootstrap_draws="count",
        )
        .reset_index()
    )


def build_predictors() -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = [load_indicator(code, name) for code, name in PREDICTOR_SPECS.items()]
    panel = outer_merge(frames)
    panel["log_gdp_per_capita_ppp"] = np.log(panel["gdp_per_capita_ppp"].where(panel["gdp_per_capita_ppp"] > 0))
    panel = panel.drop(columns=["gdp_per_capita_ppp"])

    sparse = []
    coverage = []
    for code, name in SPARSE_SPECS.items():
        frame = load_indicator(code, name)
        sparse.append(frame)
        by_country = frame.groupby("iso3")["year"].nunique()
        coverage.append(
            {
                "code": code,
                "feature": name,
                "rows": len(frame),
                "countries": frame["iso3"].nunique(),
                "median_country_years": float(by_country.median()) if len(by_country) else 0,
                "first_year": frame["year"].min() if len(frame) else np.nan,
                "last_year": frame["year"].max() if len(frame) else np.nan,
            }
        )
    sparse_panel = outer_merge(sparse)
    sparse_panel["time_tax_gap_hours_day"] = 24 * (
        sparse_panel["unpaid_work_female_pct_day"] - sparse_panel["unpaid_work_male_pct_day"]
    ) / 100
    sparse_panel["account_gap_pp"] = sparse_panel["account_male_pct"] - sparse_panel["account_female_pct"]
    sparse_panel["internet_gap_pp"] = sparse_panel["internet_male_pct"] - sparse_panel["internet_female_pct"]
    return panel, pd.DataFrame(coverage)


def make_model_panel(delays: pd.DataFrame, predictors: pd.DataFrame) -> pd.DataFrame:
    joint = delays[delays["domain"] == "joint"].copy()
    panel = joint.merge(predictors, on=["country", "iso3", "year"], how="left")
    panel = panel.sort_values(["iso3", "year"])
    panel["delay_change_1y"] = panel.groupby("iso3")["delay_years"].diff()
    panel["delay_change_3y"] = panel.groupby("iso3")["delay_years"].diff(3) / 3
    future = panel[["iso3", "year", "delay_years"]].copy()
    future["year"] -= HORIZON
    future = future.rename(columns={"delay_years": "target_delay"})
    panel = panel.merge(future, on=["iso3", "year"], how="left")
    panel["target_year"] = panel["year"] + HORIZON
    panel["target_change"] = panel["target_delay"] - panel["delay_years"]
    return panel


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "n": int(len(y_true)),
        "mae_years": float(mean_absolute_error(y_true, y_pred)),
        "rmse_years": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def fit_predictive_models(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, object, list[str]]:
    features = [
        "delay_years",
        "delay_change_1y",
        "delay_change_3y",
        "rural_population_pct",
        "rural_electricity_pct",
        "log_gdp_per_capita_ppp",
        "government_effectiveness",
        "fertility_rate",
        "internet_total_pct",
    ]
    data = panel[panel["target_delay"].notna() & ~panel["left_censored"]].copy()
    train = data[data["target_year"] <= 2016]
    valid = data[data["target_year"].between(2017, 2020)]
    test = data[data["target_year"] >= 2021]

    prep_linear = ColumnTransformer(
        [("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())]), features)]
    )
    candidates = []
    for alpha in [0.001, 0.01, 0.05, 0.1, 0.5]:
        pipe = Pipeline([("prep", prep_linear), ("model", ElasticNet(alpha=alpha, l1_ratio=0.2, max_iter=20000))])
        pipe.fit(train[features], train["target_delay"])
        pred = pipe.predict(valid[features])
        candidates.append((mean_absolute_error(valid["target_delay"], pred), alpha, pipe))
    _, chosen_alpha, linear = min(candidates, key=lambda x: x[0])

    tree = Pipeline(
        [
            ("imp", SimpleImputer(strategy="median", add_indicator=True)),
            (
                "model",
                HistGradientBoostingRegressor(
                    learning_rate=0.05,
                    max_iter=250,
                    max_leaf_nodes=15,
                    min_samples_leaf=30,
                    l2_regularization=1.0,
                    random_state=42,
                ),
            ),
        ]
    )
    tree.fit(train[features], train["target_delay"])

    rows = []
    predictions = []
    for split_name, split in [("validation", valid), ("test", test)]:
        y = split["target_delay"].to_numpy()
        for model_name, model in [
            ("persistence", None),
            (f"elastic_net_alpha_{chosen_alpha}", linear),
            ("hist_gradient_boosting", tree),
        ]:
            pred = split["delay_years"].to_numpy() if model is None else model.predict(split[features])
            row = {"split": split_name, "model": model_name, **metrics(y, pred)}
            actual_direction = np.sign(y - split["delay_years"].to_numpy())
            pred_direction = np.sign(pred - split["delay_years"].to_numpy())
            row["direction_accuracy"] = float(np.mean(actual_direction == pred_direction))
            rows.append(row)
            if split_name == "test":
                p = split[["iso3", "country", "year", "target_year", "delay_years", "target_delay"]].copy()
                p["model"] = model_name
                p["prediction"] = pred
                predictions.append(p)
    return pd.DataFrame(rows), pd.concat(predictions, ignore_index=True), tree, features


def simulate_first_passage(panel: pd.DataFrame, max_years: int = 15, n_sims: int = 1000) -> pd.DataFrame:
    """Baseline stochastic drift model for delay; external predictors held at latest observed values."""
    feature_cols = [
        "delay_years",
        "delay_change_1y",
        "delay_change_3y",
        "rural_population_pct",
        "rural_electricity_pct",
        "log_gdp_per_capita_ppp",
        "government_effectiveness",
        "fertility_rate",
        "internet_total_pct",
    ]
    drift = panel.copy()
    next_delay = drift[["iso3", "year", "delay_years"]].copy()
    next_delay["year"] -= 1
    next_delay = next_delay.rename(columns={"delay_years": "next_delay"})
    drift = drift.merge(next_delay, on=["iso3", "year"], how="left")
    drift["delta_next"] = drift["next_delay"] - drift["delay_years"]
    train = drift[
        drift["delta_next"].notna()
        & ~drift["left_censored"]
        & (drift["year"] <= 2021)
    ].copy()
    # Manual ridge fit avoids unstable recursive pipeline behavior when thousands
    # of identical simulation rows are passed through compiled BLAS routines.
    x_train = train[feature_cols].astype(float)
    medians = x_train.median()
    x_train = x_train.fillna(medians)
    means = x_train.mean()
    stds = x_train.std().replace(0, 1.0)
    xz = ((x_train - means) / stds).to_numpy(dtype=float)
    y = train["delta_next"].to_numpy(dtype=float)
    y_mean = float(np.mean(y))
    alpha = 20.0
    xtx = np.einsum("ni,nj->ij", xz, xz)
    xty = np.einsum("ni,n->i", xz, y - y_mean)
    coef = np.linalg.solve(xtx + alpha * np.eye(xz.shape[1]), xty)

    def predict_drift(frame: pd.DataFrame) -> np.ndarray:
        xx = frame[feature_cols].astype(float).fillna(medians)
        zz = ((xx - means) / stds).to_numpy(dtype=float)
        return y_mean + np.sum(zz * coef.reshape(1, -1), axis=1)

    resid = y - predict_drift(train)
    resid = resid[np.isfinite(resid)]
    # Trim extreme matching jumps; these reflect discrete year matching more than annual shocks.
    lo, hi = np.quantile(resid, [0.02, 0.98])
    resid = np.clip(resid, lo, hi)

    latest = panel.sort_values("year").groupby("iso3", as_index=False).tail(1)
    latest = latest[(latest["delay_years"] > 0) & ~latest["left_censored"]].copy()
    rows = []
    for _, row in latest.iterrows():
        d0 = float(row["delay_years"])
        threshold = 0.5 * d0
        paths = np.full(n_sims, min(d0, 30.0))
        passed = np.full(n_sims, np.nan)
        x = row[feature_cols].to_dict()
        last_delta = 0.0 if pd.isna(x["delay_change_1y"]) else float(x["delay_change_1y"])
        for h in range(1, max_years + 1):
            sim_frame = pd.DataFrame([x] * n_sims)
            sim_frame["delay_years"] = paths
            sim_frame["delay_change_1y"] = last_delta
            mu = np.clip(predict_drift(sim_frame), -2.0, 2.0)
            shock = RNG.choice(resid, size=n_sims, replace=True)
            new_paths = np.clip(paths + mu + shock, 0.0, 30.0)
            newly = np.isnan(passed) & (new_paths <= threshold)
            passed[newly] = h
            last_delta = float(np.nanmedian(new_paths - paths))
            paths = new_paths
        finite = passed[np.isfinite(passed)]
        rows.append(
            {
                "iso3": row["iso3"],
                "country": row["country"],
                "as_of_year": int(row["year"]),
                "current_delay": d0,
                "half_delay_threshold": threshold,
                "prob_halve_by_2030": float(np.mean(passed <= max(0, 2030 - int(row["year"])))),
                "prob_halve_within_10y": float(np.mean(passed <= 10)),
                "median_first_passage_years": float(np.median(finite)) if len(finite) >= n_sims / 2 else np.nan,
                "prob_not_reached_15y": float(np.mean(np.isnan(passed))),
            }
        )
    return pd.DataFrame(rows)


def make_figures(delays: pd.DataFrame, model_metrics: pd.DataFrame, fpt: pd.DataFrame) -> None:
    plt.style.use("default")
    colors = {"education": "#C58A00", "employment": "#D15B35", "joint": "#2E6F95"}
    latest = delays.sort_values("year").groupby(["iso3", "domain"], as_index=False).tail(1)
    latest = latest[~latest["left_censored"]]
    order = latest[latest["domain"] == "joint"].nlargest(20, "delay_years")["iso3"]
    plot = latest[latest["iso3"].isin(order)].pivot(index=["iso3", "country"], columns="domain", values="delay_years")
    plot = plot.reindex(order, level="iso3")
    ax = plot[[c for c in ["education", "employment", "joint"] if c in plot]].plot(
        kind="barh", figsize=(10, 8), color=[colors[c] for c in ["education", "employment", "joint"] if c in plot]
    )
    ax.invert_yaxis()
    ax.set_xlabel("Estimated historical opportunity delay (years)")
    ax.set_ylabel("")
    ax.set_title("Largest estimated gender opportunity delays\nLatest available year; uncensored matches only")
    ax.grid(axis="x", color="#dddddd", linewidth=0.7)
    plt.tight_layout()
    plt.savefig(OUT / "latest_delay_top20.png", dpi=180)
    plt.close()

    test = model_metrics[model_metrics["split"] == "test"].sort_values("mae_years")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(test["model"], test["mae_years"], color="#2E6F95")
    ax.invert_yaxis()
    ax.set_xlabel("MAE (development years)")
    ax.set_title("Three-year-ahead prediction error")
    ax.grid(axis="x", color="#dddddd", linewidth=0.7)
    plt.tight_layout()
    plt.savefig(OUT / "model_mae.png", dpi=180)
    plt.close()

    fp = fpt.dropna(subset=["prob_halve_by_2030"]).sort_values("prob_halve_by_2030")
    fp = pd.concat([fp.head(10), fp.tail(10)]).drop_duplicates("iso3")
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(fp["country"], fp["prob_halve_by_2030"], color="#C58A00")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Modeled probability")
    ax.set_title("Probability of halving current opportunity delay by 2030\nBaseline stochastic scenario")
    ax.grid(axis="x", color="#dddddd", linewidth=0.7)
    plt.tight_layout()
    plt.savefig(OUT / "first_passage_2030.png", dpi=180)
    plt.close()


def main() -> None:
    print("stage: outcomes", flush=True)
    long, outcome_coverage = build_outcome_panel()
    scores = build_scores(long)
    print("stage: delays", flush=True)
    delay_parts = [
        compute_delay_for_domain(scores, "education_score_smooth", "education"),
        compute_delay_for_domain(scores, "employment_score_smooth", "employment"),
        compute_delay_for_domain(scores, "joint_score_smooth", "joint"),
    ]
    delays = pd.concat(delay_parts, ignore_index=True)
    print("stage: bootstrap", flush=True)
    bootstrap = bootstrap_latest_delay(scores, long, n_draws=100)
    print("stage: predictors", flush=True)
    predictors, sparse_coverage = build_predictors()
    model_panel = make_model_panel(delays, predictors)
    print("stage: predictive models", flush=True)
    model_metrics, model_predictions, _, features = fit_predictive_models(model_panel)
    print("stage: first passage", flush=True)
    fpt = simulate_first_passage(model_panel)

    latest = delays.sort_values("year").groupby(["iso3", "domain"], as_index=False).tail(1)
    latest_joint = latest[latest["domain"] == "joint"].merge(bootstrap, on="iso3", how="left")
    latest_wide = latest.pivot_table(index=["iso3", "country", "year"], columns="domain", values="delay_years").reset_index()
    latest_wide["desynchronization_sd_years"] = latest_wide[["education", "employment"]].std(axis=1)

    outcome_coverage.to_csv(OUT / "outcome_indicator_coverage.csv", index=False)
    sparse_coverage.to_csv(OUT / "sparse_predictor_coverage.csv", index=False)
    long.to_csv(OUT / "outcomes_long.csv.gz", index=False, compression="gzip")
    scores.to_csv(OUT / "opportunity_scores.csv.gz", index=False, compression="gzip")
    delays.to_csv(OUT / "domain_delays.csv.gz", index=False, compression="gzip")
    latest_joint.to_csv(OUT / "latest_joint_development_year.csv", index=False)
    latest_wide.to_csv(OUT / "latest_domain_delays.csv", index=False)
    model_panel.to_csv(OUT / "predictive_model_panel.csv.gz", index=False, compression="gzip")
    model_metrics.to_csv(OUT / "predictive_model_metrics.csv", index=False)
    model_predictions.to_csv(OUT / "predictive_model_test_predictions.csv", index=False)
    fpt.to_csv(OUT / "first_passage_estimates.csv", index=False)

    summary = {
        "analysis_period": [START_YEAR, END_YEAR],
        "countries_in_outcomes": int(long["iso3"].nunique()),
        "country_year_sex_score_rows": int(scores["joint_score"].notna().sum()),
        "latest_joint_delay_countries": int(len(latest_joint)),
        "latest_joint_uncensored_countries": int((~latest_joint["left_censored"]).sum()),
        "latest_joint_bootstrap_90pct_median_width": float((latest_joint["delay_p95"] - latest_joint["delay_p05"]).median()),
        "model_features": features,
        "test_best_model": model_metrics[model_metrics["split"] == "test"].sort_values("mae_years").iloc[0].to_dict(),
        "fpt_countries": int(len(fpt)),
        "method_note": "Development-year uncertainty is indicator-resampling bootstrap, not a Bayesian credible interval. First-passage estimates are baseline stochastic scenarios with latest external predictors held fixed.",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # Figures last, in a child process: a native crash in matplotlib (SIGABRT seen on macOS with the
    # CommandLineTools Python 3.9 + vendored wheels) can no longer take down the run or lose outputs.
    print("stage: figures", flush=True)
    render_figures_safely()


def render_figures_from_outputs() -> None:
    delays = pd.read_csv(OUT / "domain_delays.csv.gz")
    model_metrics = pd.read_csv(OUT / "predictive_model_metrics.csv")
    fpt = pd.read_csv(OUT / "first_passage_estimates.csv")
    make_figures(delays, model_metrics, fpt)


def render_figures_safely() -> None:
    import subprocess, sys
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--figures-only"])
    if r.returncode != 0:
        print(f"WARNING: figure rendering failed (exit code {r.returncode}); all CSV/JSON outputs are saved. "
              f"Re-run with a different Python: python3 {Path(__file__).name} --figures-only", flush=True)


if __name__ == "__main__":
    import sys
    if "--figures-only" in sys.argv:
        render_figures_from_outputs()
        raise SystemExit(0)
    main()
