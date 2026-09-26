"""
Rural–urban analysis, step 1: build the panel.
(a) Time-tax infrastructure gap (urban minus rural, percentage points), annual:
    clean cooking EG.CFT.ACCS, electricity EG.ELC.ACCS, basic water SH.H2O.BASW, basic sanitation SH.STA.BASS
    composite = mean of available component gaps (>=3 of 4).
(b) Women's jobs gap (JOIN, survey years): female non-agricultural employment share, urban minus rural (pp).
Also: JOIN gender wage gap rural/urban, and rural/urban female population share for context.
"""
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs" / "rural_urban"; CMB = ROOT / "outputs" / "world_bank_sources" / "combined"
META = ROOT / "outputs" / "world_bank_indicators_wide_2010_2024.csv"
INFRA = {"cooking": ("EG.CFT.ACCS", "002_WDI"), "electricity": ("EG.ELC.ACCS", "002_WDI"), "water": ("SH.H2O.BASW", "016_HNP"), "sanitation": ("SH.STA.BASS", "016_HNP")}
def load(src, cols):
    w = pd.read_parquet(CMB / f"{src}_wide.parquet", columns=["iso3", "year", "is_aggregate"] + cols)
    return w[~w.is_aggregate].drop(columns="is_aggregate").set_index(["iso3", "year"])
parts = []
for k, (code, src) in INFRA.items():
    x = load(src, [f"{code}.RU.ZS", f"{code}.UR.ZS"]).rename(columns={f"{code}.RU.ZS": f"{k}_rural", f"{code}.UR.ZS": f"{k}_urban"})
    x[f"{k}_gap"] = x[f"{k}_urban"] - x[f"{k}_rural"]; parts.append(x)
A = pd.concat(parts, axis=1)
gaps = [f"{k}_gap" for k in INFRA]
A["infra_gap"] = A[gaps].mean(axis=1).where(A[gaps].notna().sum(axis=1) >= 3)
A["infra_rural"] = A[[f"{k}_rural" for k in INFRA]].mean(axis=1).where(A[gaps].notna().sum(axis=1) >= 3)
A["infra_urban"] = A[[f"{k}_urban" for k in INFRA]].mean(axis=1).where(A[gaps].notna().sum(axis=1) >= 3)
J = load("086_JON", ["JI.EMP.NAGR.FE.RU.ZS", "JI.EMP.NAGR.FE.UR.ZS", "JI.WAG.GNDR.RU", "JI.WAG.GNDR.UR", "JI.TLF.ACTI.RU.ZS", "JI.TLF.ACTI.UR.ZS"] if True else [])
J = J.rename(columns={"JI.EMP.NAGR.FE.RU.ZS": "fem_nonag_rural", "JI.EMP.NAGR.FE.UR.ZS": "fem_nonag_urban", "JI.WAG.GNDR.RU": "wage_gap_rural",
                      "JI.WAG.GNDR.UR": "wage_gap_urban", "JI.TLF.ACTI.RU.ZS": "lfpr_rural_all", "JI.TLF.ACTI.UR.ZS": "lfpr_urban_all"})
J["jobs_gap"] = J.fem_nonag_urban - J.fem_nonag_rural
X = load("002_WDI", ["SP.RUR.TOTL.ZS", "NY.GDP.PCAP.PP.KD", "SP.DYN.TFRT.IN"]).rename(columns={"SP.RUR.TOTL.ZS": "rural_pop_share", "NY.GDP.PCAP.PP.KD": "gdppc_ppp", "SP.DYN.TFRT.IN": "fertility"})
Pn = A.join(J, how="outer").join(X, how="left").reset_index()
Pn = Pn[Pn.year.between(1990, 2024)]
meta = pd.read_csv(META, usecols=["country_code", "country_name", "region_name", "income_level_name"]).drop_duplicates("country_code").rename(columns={"country_code": "iso3"})
Pn = Pn.merge(meta, on="iso3", how="inner")
Pn.to_csv(OUT / "rural_urban_panel.csv.gz", index=False)
def cov(col, y0=2000):
    s = Pn[(Pn.year >= y0)].dropna(subset=[col]); n = s.groupby("iso3").size()
    return dict(var=col, economies=n.size, obs=len(s), median_years=float(n.median()) if len(n) else 0, first=int(s.year.min()) if len(s) else None, last=int(s.year.max()) if len(s) else None,
                median_2019=float(Pn[Pn.year == 2019][col].median()) if col in Pn else None)
C = pd.DataFrame([cov(c) for c in gaps + ["infra_gap", "jobs_gap", "wage_gap_rural", "wage_gap_urban"]]).round(2)
C.to_csv(OUT / "coverage.csv", index=False); print(C.to_string(index=False))
# quick descriptive: median gaps over time
print(Pn.groupby("year")[["infra_gap", "cooking_gap", "water_gap", "electricity_gap", "sanitation_gap"]].median().loc[[2000, 2005, 2010, 2015, 2020, 2023]].round(1).to_string())
j = Pn.dropna(subset=["jobs_gap"]); j["decade"] = (j.year // 10) * 10
print(j.groupby("decade").agg(n=("jobs_gap", "size"), econ=("iso3", "nunique"), jobs_gap_med=("jobs_gap", "median"), rural_med=("fem_nonag_rural", "median"), urban_med=("fem_nonag_urban", "median")).round(1).to_string())
print("JOIN obs per economy since 2000:", j[j.year >= 2000].groupby("iso3").size().describe().round(1).to_dict())
