"""
Step 1 - Build the rural/urban x women/men indicator panel.

Output
  outputs/panel_long.csv        iso, year, group (RW/UW/RM/UM), indicator, dimension, value, y
                                 value = share (0-1, oriented so higher = better) or years
                                 y     = modelling scale (logit for shares), standardised per indicator
  outputs/macro_panel.csv       national controls
  outputs/wage_ratio_panel.csv  female/male wage ratio in rural and urban areas (direct measure)
  outputs/validation_rural_women.csv  check of the rural-women approximation
  outputs/coverage.csv          observations per indicator x group
"""
import numpy as np
import pandas as pd

import config as C
from common import expit, logit, read_indicator, country_table


def _marginals(folder, base, fam, divisor):
    out = {}
    for k, pat in C.SUFFIX[fam].items():
        out[k] = read_indicator(folder, pat.format(b=base)) / divisor
    return pd.DataFrame(out)


def build_indicator(name, dim, folder, base, fam, kind, scale, divisor, sign):
    m = _marginals(folder, base, fam, divisor)
    if m.empty:
        return pd.DataFrame()
    if kind == "hh":
        g = pd.DataFrame({"RW": m["R"], "UW": m["U"], "RM": m["R"], "UM": m["U"]})
    elif scale == "prop":
        lT, lR, lU = logit(m["T"]), logit(m["R"]), logit(m["U"])
        lF, lM = logit(m["F"]), logit(m["M"])
        g = pd.DataFrame({
            "RW": expit(lR + lF - lT), "UW": expit(lU + lF - lT),
            "RM": expit(lR + lM - lT), "UM": expit(lU + lM - lT),
        })
    else:  # continuous (years of schooling): additive decomposition
        g = pd.DataFrame({
            "RW": m["R"] + m["F"] - m["T"], "UW": m["U"] + m["F"] - m["T"],
            "RM": m["R"] + m["M"] - m["T"], "UM": m["U"] + m["M"] - m["T"],
        }).clip(lower=0)
    if sign < 0 and scale == "prop":
        g = 1 - g
    long = g.stack().rename("value").reset_index()
    long.columns = ["iso", "year", "group", "value"]
    long["indicator"], long["dimension"], long["scale"] = name, dim, scale
    long["kind"] = kind
    return long.dropna(subset=["value"])


def build_direct(name, dim, folder, rw_id, uw_id, divisor, sign):
    rw = read_indicator(folder, rw_id) / divisor
    uw = read_indicator(folder, uw_id) / divisor
    g = pd.DataFrame({"RW": rw, "UW": uw})
    if sign < 0:
        g = 1 - g
    long = g.stack().rename("value").reset_index()
    long.columns = ["iso", "year", "group", "value"]
    long["indicator"], long["dimension"], long["scale"], long["kind"] = name, dim, "prop", "direct"
    return long.dropna(subset=["value"])


def validate_approximation():
    """Compare the log-odds approximation with the direct rural-women measure.
    Non-agricultural employment share = 1 - agricultural share; 086_JON has it for
    women in rural / urban areas (JI.EMP.NAGR.FE.RU/UR.ZS) and for the marginals."""
    f = "086_JON"
    na = {k: 1 - read_indicator(f, i) for k, i in
          dict(T="JI.EMP.AGRI.ZS", R="JI.EMP.AGRI.RU.ZS", U="JI.EMP.AGRI.UR.ZS", F="JI.EMP.AGRI.FE.ZS").items()}
    d = pd.DataFrame(na)
    d["RW_true"] = read_indicator(f, "JI.EMP.NAGR.FE.RU.ZS")
    d["UW_true"] = read_indicator(f, "JI.EMP.NAGR.FE.UR.ZS")
    d = d.dropna()
    if d.empty:
        return None
    d["RW_logit"] = expit(logit(d.R) + logit(d.F) - logit(d["T"]))
    d["UW_logit"] = expit(logit(d.U) + logit(d.F) - logit(d["T"]))
    d["RW_mult"] = (d.R * d.F / d["T"]).clip(0, 1)
    d["RW_naive"] = d.R
    rows = []
    for est in ["RW_logit", "RW_mult", "RW_naive"]:
        e = d[est] - d.RW_true
        rows.append(dict(method=est, n=len(d), mae=e.abs().mean(), bias=e.mean(),
                         corr=np.corrcoef(d[est], d.RW_true)[0, 1]))
    gap_true, gap_est = d.UW_true - d.RW_true, d.UW_logit - d.RW_logit
    rows.append(dict(method="gap_UW_minus_RW_logit", n=len(d), mae=(gap_est - gap_true).abs().mean(),
                     bias=(gap_est - gap_true).mean(), corr=np.corrcoef(gap_est, gap_true)[0, 1]))
    return pd.DataFrame(rows)


def main():
    parts = [build_indicator(*spec) for spec in C.INDICATORS]
    parts += [build_direct(*spec) for spec in C.DIRECT]
    panel = pd.concat([p for p in parts if len(p)], ignore_index=True)

    # modelling scale: logit for shares, raw for years; then standardise per indicator
    panel["y"] = np.where(panel["scale"] == "prop", logit(panel["value"].values), panel["value"].values)
    st = panel.groupby("indicator")["y"].agg(["mean", "std"])
    panel = panel.join(st, on="indicator")
    panel["y"] = (panel["y"] - panel["mean"]) / panel["std"]
    panel = panel.drop(columns=["mean", "std"])
    ct = country_table()
    panel["region"] = ct.reindex(panel["iso"])["region"].values
    panel.to_csv(C.OUT_DIR / "panel_long.csv", index=False)
    st.to_csv(C.OUT_DIR / "indicator_scaling.csv")

    cov = (panel.groupby(["dimension", "indicator", "group"])
           .agg(n_obs=("y", "size"), n_countries=("iso", "nunique"), first=("year", "min"), last=("year", "max"))
           .reset_index())
    cov.to_csv(C.OUT_DIR / "coverage.csv", index=False)

    macro = pd.DataFrame({k: read_indicator(f, i) for k, (f, i) in C.MACRO.items()})
    macro["log_gdppc_ppp"] = np.log(macro["log_gdppc_ppp"])
    macro.reset_index().to_csv(C.OUT_DIR / "macro_panel.csv", index=False)

    f, ru, ur, tot = C.WAGE_RATIO
    wr = pd.DataFrame({"rural": read_indicator(f, ru), "urban": read_indicator(f, ur), "total": read_indicator(f, tot)})
    wr.reset_index().to_csv(C.OUT_DIR / "wage_ratio_panel.csv", index=False)

    val = validate_approximation()
    if val is not None:
        val.to_csv(C.OUT_DIR / "validation_rural_women.csv", index=False)
        print("\nRural-women approximation check (non-agricultural employment share):")
        print(val.round(3).to_string(index=False))

    print(f"\npanel rows: {len(panel):,}  countries: {panel.iso.nunique()}  indicators: {panel.indicator.nunique()}")
    print(cov[cov.group == "RW"].to_string(index=False))


if __name__ == "__main__":
    main()
