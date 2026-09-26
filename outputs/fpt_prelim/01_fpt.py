"""
Preliminary First-Passage Time (FPT) analysis — "She Waits", part 1.
Per country x indicator:
  latent female state Z_t follows random walk with drift; observed = Z_t + noise (Kalman handles missing years)
  model: statsmodels UnobservedComponents('lldtrend') on transformed scale
  threshold Z* = men's latent level in the last year (uncertain, drawn from its filtered dist.)
  T* = inf{h>=0 : Z_{T+h} >= Z*}, simulated from the terminal state distribution (level+drift jointly) + future shocks
Also backward delay D = years since men's smoothed level was at women's current level.
Usage: python3 01_fpt.py [fit_end_year] [out_tag]
"""
import sys, warnings, numpy as np, pandas as pd
from statsmodels.tsa.statespace.structural import UnobservedComponents
warnings.filterwarnings("ignore")
W="world_bank_sources/002_WDI"
FIT_END=int(sys.argv[1]) if len(sys.argv)>1 else 2024
TAG=sys.argv[2] if len(sys.argv)>2 else "main"
FIT_START=2000; H=2050-FIT_END; NSIM=4000
rng=np.random.default_rng(7)
# code, label, higher_is_better, transform
IND=[("SL.TLF.CACT.FE.ZS","Labor force participation (15+, ILO modeled)",True,"logit"),
     ("SL.EMP.WORK.FE.ZS","Wage & salaried workers (% of employed, ILO modeled)",True,"logit"),
     ("SL.EMP.VULN.FE.ZS","Vulnerable employment (% of employed, ILO modeled)",False,"logit"),
     ("SE.SEC.CMPT.LO.FE.ZS","Lower secondary completion rate",True,"log"),
     ("SE.TER.ENRR.FE","Tertiary gross enrollment",True,"log"),
     ("FX.OWN.TOTL.FE.ZS","Account ownership (15+, Findex)",True,"logit")]
meta=pd.read_csv("world_bank_indicators_wide_2010_2024.csv",usecols=["country_code","country_name","region_name","income_level_name"]).drop_duplicates("country_code")
C=set(meta.country_code)
def tf(x,t):
    x=np.asarray(x,float)
    if t=="logit": p=np.clip(x/100,0.005,0.995); return np.log(p/(1-p))
    return np.log(np.clip(x,0.5,None))
def itf(z,t): return 100/(1+np.exp(-z)) if t=="logit" else np.exp(z)
def load(code):
    d=pd.read_csv(f"{W}/{code}.csv.gz"); d=d[d.iso3.isin(C)&(d.date<=FIT_END)].dropna(subset=["value"])
    return d.pivot_table(index="date",columns="iso3",values="value")
def fit(y):
    """y: pd.Series indexed by year (full annual grid incl NaN). returns filtered terminal mean/cov, smoothed level, sigma_level"""
    m=UnobservedComponents(y.values,level="lldtrend")
    try: r=m.fit(disp=False,maxiter=200)
    except Exception: return None
    a=r.filtered_state[:,-1]; P=r.filtered_state_cov[:,:,-1]
    sl=np.sqrt(max(r.params[list(r.model.param_names).index("sigma2.level")],0))
    return a,P,r.smoothed_state[0],sl
out=[]
SEL=[int(x) for x in sys.argv[3].split(",")] if len(sys.argv)>3 else range(len(IND))
for code,label,hib,t in [IND[i] for i in SEL]:
    F=load(code); M=load(code.replace(".FE",".MA"))
    yrs=np.arange(1990,FIT_END+1)
    for c in sorted(set(F.columns)&set(M.columns)):
        f=F[c].reindex(yrs); mm=M[c].reindex(yrs)
        fw=f.loc[FIT_START:]
        nobs=fw.notna().sum()
        if nobs<4 or fw.last_valid_index()<FIT_END-6: continue
        s=1 if hib else -1   # orient so "higher = better"
        rf=fit(pd.Series(s*tf(fw,t),index=fw.index)); rm=fit(pd.Series(s*tf(mm,t),index=yrs))
        if rf is None or rm is None: continue
        aF,PF,smF,slF=rf; aM,PM,smM,slM=rm
        # simulate
        L=rng.multivariate_normal(aF,PF+1e-10*np.eye(2),NSIM)          # (level, drift)
        zstar=rng.normal(aM[0],np.sqrt(max(PM[0,0],0)),NSIM)
        lev=L[:,0].copy(); T=np.full(NSIM,np.inf); T[lev>=zstar]=0
        for h in range(1,H+1):
            lev=lev+L[:,1]+rng.normal(0,slF,NSIM)
            hit=np.isinf(T)&(lev>=zstar); T[hit]=h
        pr=lambda k:(T<=k).mean()
        med=np.median(T); 
        # backward delay: years since men's smoothed level <= women's current level (latent)
        cur=aF[0]; below=np.where(smM<=cur)[0]
        D=(FIT_END-yrs[below[-1]]) if len(below) else np.nan
        Dcens=len(below)==0
        # women already ahead of men today?
        out.append(dict(indicator=code,label=label,iso3=c,n_obs=int(nobs),last_obs=int(fw.last_valid_index()),
            women_now=float(itf(s*aF[0],t)),men_now=float(itf(s*aM[0],t)),
            drift_pp_per_yr=float(itf(s*(aF[0]+aF[1]),t)-itf(s*aF[0],t)),
            p_drift_pos=float((L[:,1]>0).mean()),
            p_reached_now=pr(0),p_by_2030=pr(2030-FIT_END),p_by_2035=pr(2035-FIT_END),p_by_2050=pr(H),
            median_T=(np.nan if np.isinf(med) else float(med)),
            T_q10=float(np.quantile(T,.1)) if np.isfinite(np.quantile(T,.1)) else np.nan,
            T_q90=float(np.quantile(T,.9)) if np.isfinite(np.quantile(T,.9)) else np.nan,
            back_delay_D=D,back_delay_censored=Dcens,aF0=aF[0],aF1=aF[1],PF00=PF[0,0],PF01=PF[0,1],PF11=PF[1,1],slF=slF,aM0=aM[0],PM00=PM[0,0],orient=s,transform=t,**{f'p_h{k}':pr(k) for k in (4,8,12)}))
    print(code,"done",flush=True)
R=pd.DataFrame(out).merge(meta,left_on="iso3",right_on="country_code",how="left").drop(columns="country_code")
def status(r):
    if r.p_reached_now>=0.5: return "Already at men's level"
    if r.p_by_2050<0.5: return "Unlikely by 2050"
    return "Median wait %d yrs"%r.median_T
R["status"]=R.apply(status,axis=1)
suf="" if len(sys.argv)<=3 else "_part"+sys.argv[3].replace(",","-")
R.to_csv(f"fpt_prelim/fpt_results_{TAG}{suf}.csv",index=False)
print(R.groupby("indicator")[["p_reached_now","p_by_2030","p_by_2050"]].mean().round(3))
