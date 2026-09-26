import pandas as pd, os, re, glob
W="world_bank_sources/002_WDI"
countries=set(pd.read_csv("world_bank_indicators_wide_2010_2024.csv",usecols=["country_code"]).country_code)
rows=[]
for f in sorted(glob.glob(f"{W}/*.FE*.csv.gz")):
    code=os.path.basename(f)[:-7]
    mcode=code.replace(".FE",".MA")
    mf=f"{W}/{mcode}.csv.gz"
    if not os.path.exists(mf): continue
    a=pd.read_csv(f); a=a[a.iso3.isin(countries)].dropna(subset=["value"])
    b=pd.read_csv(mf); b=b[b.iso3.isin(countries)].dropna(subset=["value"])
    m=a.merge(b,on=["iso3","date"])
    if len(m)==0: continue
    r=m[m.date>=2000]
    rows.append(dict(code=code,n_pairs=len(m),yr_min=m.date.min(),yr_max=m.date.max(),
      n_cty=m.iso3.nunique(),obs_per_cty_2000=len(r)/max(r.iso3.nunique(),1),n_cty_2000=r.iso3.nunique()))
d=pd.DataFrame(rows).sort_values("n_pairs",ascending=False)
d.to_csv("fpt_prelim/fe_ma_pair_coverage.csv",index=False)
pd.set_option("display.width",200); print(d.head(60).to_string(index=False))
