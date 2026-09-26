import sys; sys.argv=[""]
exec(open("fpt_prelim/03_simulate.py").read().split('if __name__')[0])
import numpy as np, pandas as pd
main=load("main"); LB={"SL.EMP.VULN.FE.ZS"}; ev=[]
from scipy.special import expit
def itf(z,t): return 100*expit(z) if t=="logit" else np.exp(z)
for Y,h in [(2012,12),(2016,8)]:
    b=load(f"backtest{Y}")
    for name in ["plugin","eb"]:
        bb=VARIANTS[name](b); s=sim(bb,h,[0,h],thr="half")
        # realized: women's 2024 level (orig scale) crossed the halfway value defined at Y
        bb=bb.assign(half=[itf(o*(a+0.5*(m-a)),t) for o,a,m,t in zip(bb.orient,bb.aF0,bb.aM0,bb["transform"])])
        m=bb[["indicator","iso3","half","women_now","men_now"]].merge(s,on=["indicator","iso3"]).merge(main[["indicator","iso3","women_now","last_obs"]].rename(columns={"women_now":"w24","last_obs":"lo24"}),on=["indicator","iso3"])
        lb=m.indicator.isin(LB)
        m=m[(m.lo24>=2022)&np.where(lb,m.women_now>m.men_now,m.women_now<m.men_now)]   # only where women behind at Y
        lb=m.indicator.isin(LB); m["y"]=np.where(lb,m.w24<=m.half,m.w24>=m.half).astype(int); m["p"]=m[f"p_h{h}"]; m["Y"]=Y; m["variant"]=name; ev.append(m)
E=pd.concat(ev)
def summ(g):
    br=((g.p-g.y)**2).mean(); base=g.y.mean(); hi=g[g.p>=.8]; lo=g[g.p<=.2]
    return pd.Series(dict(n=len(g),event_rate=base,mean_p=g.p.mean(),brier=br,BSS=1-br/(base*(1-base)),hit_p_ge80=hi.y.mean(),hit_p_le20=lo.y.mean()))
S=E.groupby(["Y","variant"])[["p","y"]].apply(summ).round(3); print(S.to_string())
print(E[E.variant=="eb"].groupby(["indicator"])[["p","y"]].apply(summ).round(3).to_string())
S.to_csv("fpt_prelim/backtest_halfgap_summary.csv"); E.to_csv("fpt_prelim/backtest_halfgap.csv",index=False)
