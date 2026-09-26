"""
Combine each downloaded World Bank source folder (e.g. 002_WDI/, 012_EDS/) into one table per source.
Rows = economy x year; one column per indicator code. Re-run anytime as downloads continue (rebuilds from scratch).

Outputs (world_bank_sources/combined/):
  <SRC>_wide.parquet / .csv.gz : iso3, country, year, is_aggregate, <indicator columns...>
  <SRC>_long.parquet           : iso3, country, year, indicator, value, obs_status
  <SRC>_columns.csv            : indicator code, name (if known), n_obs, n_economies, year range
Usage: python3 combine_sources.py [folder ...]    (default: every NNN_* folder)
"""
import sys, os, glob, pandas as pd
from concurrent.futures import ProcessPoolExecutor
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"combined"); os.makedirs(OUT,exist_ok=True)
ROOT=os.path.dirname(HERE)
ECON=set(pd.read_csv(os.path.join(ROOT,"world_bank_indicators_wide_2010_2024.csv"),usecols=["country_code"]).country_code)
CAT=os.path.join(ROOT,"marginalized_groups_eda","source_indicator_catalog.csv")
NAMES=pd.read_csv(CAT,usecols=["indicator_code","indicator_name"]).drop_duplicates("indicator_code").set_index("indicator_code").indicator_name.to_dict() if os.path.exists(CAT) else {}
import re
def code_of(f): return re.sub(r" \d+$","",re.sub(r"\.csv(\.gz)?$","",os.path.basename(f)))
def pick_files(folder):
    """one file per indicator: prefer .csv.gz, else plain .csv; ignore _meta files and Finder duplicates ('X 2.csv')"""
    fs={}
    for f in sorted(glob.glob(os.path.join(folder,"*.csv*"))):
        b=os.path.basename(f)
        if b.startswith("_") or b.startswith("."): continue
        c=code_of(f); dup=bool(re.search(r" \d+\.csv",b)); gz=f.endswith(".gz")
        rank=(gz, not dup)
        if c not in fs or rank>fs[c][0]: fs[c]=(rank,f)
    return [v[1] for v in fs.values()]
def read(f):
    code=code_of(f)
    try: d=pd.read_csv(f,dtype={"obs_status":str})
    except Exception as e: return code,None,str(e)      # e.g. file still being written
    d=d.dropna(subset=["value"])
    # some sources (e.g. JOIN) leave iso3 blank and put the ISO3 code in country_id
    fill=d.iso3.isna()&d.country_id.astype(str).str.fullmatch(r"[A-Z]{3}")
    d.loc[fill,"iso3"]=d.loc[fill,"country_id"]
    d=d[d.iso3.notna()&(d.iso3.astype(str).str.len()==3)]
    d["indicator"]=code; return code,d[["iso3","country","date","indicator","value","obs_status"]],None
def combine(folder):
    src=os.path.basename(folder.rstrip("/")); files=pick_files(folder)
    with ProcessPoolExecutor() as ex: res=list(ex.map(read,files,chunksize=50))
    bad=[(c,e) for c,d,e in res if e]; parts=[d for c,d,e in res if d is not None and len(d)]
    L=pd.concat(parts,ignore_index=True).rename(columns={"date":"year"})
    L["value"]=pd.to_numeric(L.value,errors="coerce")
    L["year"]=pd.to_numeric(L.year.astype(str).str.extract(r"(\d{4})")[0],errors="coerce")   # e.g. "YR2021", "2021Q1"
    L=L.dropna(subset=["value","year"]); L["year"]=L.year.astype(int)
    L.to_parquet(os.path.join(OUT,f"{src}_long.parquet"),index=False)
    names=L.drop_duplicates("iso3").set_index("iso3").country
    Wd=L.pivot_table(index=["iso3","year"],columns="indicator",values="value",aggfunc="first")
    Wd.columns.name=None; Wd=Wd.reset_index()
    Wd.insert(1,"country",Wd.iso3.map(names)); Wd.insert(3,"is_aggregate",~Wd.iso3.isin(ECON))
    Wd=Wd.sort_values(["is_aggregate","iso3","year"])
    Wd.to_parquet(os.path.join(OUT,f"{src}_wide.parquet"),index=False)
    Wd.to_csv(os.path.join(OUT,f"{src}_wide.csv.gz"),index=False)
    E=L[L.iso3.isin(ECON)]
    cols=E.groupby("indicator").agg(n_obs=("value","size"),n_economies=("iso3","nunique"),year_min=("year","min"),year_max=("year","max"))
    cols=cols.reindex(sorted(L.indicator.unique()))
    meta=os.path.join(folder,"_indicators.csv")
    if os.path.exists(meta):
        M=pd.read_csv(meta).drop_duplicates("id").set_index("id")
        for k in ["name","unit","source_org","topics","definition"][::-1]:
            if k in M: cols.insert(0,k,cols.index.map(M[k]))
    else: cols.insert(0,"name",[NAMES.get(c,"") for c in cols.index])
    cols.index.name="indicator"; cols.sort_values("n_obs",ascending=False).to_csv(os.path.join(OUT,f"{src}_columns.csv"))
    print(f"{src}: {len(files)} files -> {Wd.shape[0]} rows x {Wd.shape[1]-4} indicator cols; unreadable={len(bad)} {bad[:3]}",flush=True)
if __name__=="__main__":
    folders=sys.argv[1:] or sorted(glob.glob(os.path.join(HERE,"[0-9][0-9][0-9]_*/")))
    for f in folders: combine(f)
