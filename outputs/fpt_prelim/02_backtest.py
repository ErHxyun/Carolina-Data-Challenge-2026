import pandas as pd, numpy as np, glob
rd=lambda tag: pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"fpt_prelim/fpt_results_{tag}_part*.csv"))])
main=rd("main"); main.to_csv("fpt_prelim/fpt_results_main.csv",index=False)
LOWER_BETTER={"SL.EMP.VULN.FE.ZS"}
rows=[]
for Y,h in [(2016,8),(2012,12)]:
    b=rd(f"backtest{Y}")
    m=b.merge(main[["indicator","iso3","women_now","n_obs","last_obs"]],on=["indicator","iso3"],suffixes=("","_24"))
    m=m[(m.p_reached_now<0.5)&(m.last_obs_24>=2022)]
    lb=m.indicator.isin(LOWER_BETTER)
    m["realized"]=np.where(lb,m.women_now_24<=m.men_now,m.women_now_24>=m.men_now).astype(int)
    m["p"]=m[f"p_h{h}"]
    m["Y"]=Y
    rows.append(m)
B=pd.concat(rows)
B.to_csv("fpt_prelim/backtest_eval.csv",index=False)
def summ(g):
    br=((g.p-g.realized)**2).mean(); base=g.realized.mean()
    return pd.Series(dict(n=len(g),event_rate=base,mean_p=g.p.mean(),brier=br,brier_climatology=base*(1-base),
                          BSS=1-br/(base*(1-base)) if 0<base<1 else np.nan))
print(B.groupby(["Y","indicator"]).apply(summ).round(3).to_string())
print(B.groupby("Y").apply(summ).round(3).to_string())
B["bin"]=pd.cut(B.p,[-.01,.05,.2,.4,.6,.8,.95,1.0])
cal=B.groupby(["Y","bin"],observed=True).agg(n=("p","size"),mean_p=("p","mean"),obs_freq=("realized","mean")).round(3)
print(cal.to_string()); cal.to_csv("fpt_prelim/backtest_calibration.csv")
