"""Re-simulate FPT from saved Kalman terminal states, with variants:
 plugin : per-country MLE state (as in 01)
 eb     : empirical-Bayes partial pooling of drift within indicator x income group
 eb_fl  : eb + floor on level-shock sd at the indicator median (guards against sigma->0 MLE collapse)
"""
import pandas as pd, numpy as np, glob, sys
rng=np.random.default_rng(11)
NSIM=4000
def load(tag): return pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"fpt_prelim/fpt_results_{tag}_part*.csv"))],ignore_index=True)
def eb(df):
    df=df.copy(); df["grp"]=df.indicator+"|"+df.income_level_name.fillna("NA")
    d,v=df.aF1,df.PF11.clip(lower=1e-10)
    for g,ix in df.groupby("grp").groups.items():
        dd,vv=d[ix],v[ix]; mu=np.average(dd,weights=1/vv) if len(ix)>2 else dd.mean()
        tau2=max(dd.var()-vv.mean(),1e-6) if len(ix)>2 else 1e-2
        pv=1/(1/vv+1/tau2); df.loc[ix,"aF1"]=pv*(dd/vv+mu/tau2); df.loc[ix,"PF11"]=pv
        df.loc[ix,"PF01"]=df.loc[ix,"PF01"]*np.sqrt(pv/vv)
    return df
def floor(df):
    df=df.copy(); med=df.groupby("indicator").slF.transform("median"); df["slF"]=np.maximum(df.slF,med); return df
def sim(df,H,hs,thr='men'):
    out={f"p_h{h}":[] for h in hs}; out["median_T"]=[];out["T_q10"]=[];out["T_q90"]=[]
    for r in df.itertuples():
        Pm=np.array([[r.PF00,r.PF01],[r.PF01,r.PF11]])+1e-10*np.eye(2)
        try: L=rng.multivariate_normal([r.aF0,r.aF1],Pm,NSIM,method="eigh")
        except Exception: L=np.column_stack([np.full(NSIM,r.aF0),np.full(NSIM,r.aF1)])
        z=rng.normal(r.aM0,np.sqrt(max(r.PM00,0)),NSIM) if thr=='men' else np.full(NSIM,r.aF0+0.5*(r.aM0-r.aF0))
        lev=L[:,0].copy(); T=np.full(NSIM,np.inf); T[lev>=z]=0
        for h in range(1,H+1):
            lev=lev+L[:,1]+rng.normal(0,r.slF,NSIM); T[np.isinf(T)&(lev>=z)]=h
        for h in hs: out[f"p_h{h}"].append((T<=h).mean())
        q=np.quantile(T,[.1,.5,.9]); q=[np.nan if np.isinf(x) else x for x in q]
        out["T_q10"].append(q[0]);out["median_T"].append(q[1]);out["T_q90"].append(q[2])
    res=df[["indicator","iso3"]].copy()
    for k,v in out.items(): res[k]=v
    return res
VARIANTS={"plugin":lambda d:d,"eb":eb,"eb_fl":lambda d:floor(eb(d))}
if __name__=="__main__":
    main=load("main"); LB={"SL.EMP.VULN.FE.ZS"}
    ev=[]
    for Y,h in [(2012,12),(2016,8)]:
        b=load(f"backtest{Y}")
        for name,fn in VARIANTS.items():
            s=sim(fn(b),h,[0,h])
            m=b[["indicator","iso3","men_now"]].merge(s,on=["indicator","iso3"]).merge(main[["indicator","iso3","women_now","last_obs"]].rename(columns={"women_now":"w24","last_obs":"lo24"}),on=["indicator","iso3"])
            m=m[(m.p_h0<0.5)&(m.lo24>=2022)]
            lb=m.indicator.isin(LB); m["y"]=np.where(lb,m.w24<=m.men_now,m.w24>=m.men_now).astype(int)
            m["p"]=m[f"p_h{h}"]; m["Y"]=Y; m["variant"]=name; ev.append(m)
    E=pd.concat(ev); E.to_csv("fpt_prelim/backtest_variants.csv",index=False)
    def summ(g):
        br=((g.p-g.y)**2).mean(); base=g.y.mean()
        hi=g[g.p>=0.8]
        return pd.Series(dict(n=len(g),event_rate=base,mean_p=g.p.mean(),brier=br,BSS=1-br/(base*(1-base)),
                              n_p_ge80=len(hi),hit_rate_p_ge80=hi.y.mean() if len(hi) else np.nan))
    S=E.groupby(["Y","variant"])[["p","y"]].apply(summ).round(3); print(S.to_string()); S.to_csv("fpt_prelim/backtest_variant_summary.csv")
    S2=E.groupby(["variant","indicator"])[["p","y"]].apply(summ).round(3); print(S2[["n","event_rate","mean_p","BSS"]].to_string())
