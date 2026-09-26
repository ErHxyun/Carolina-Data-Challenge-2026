import sys; sys.argv=[""]
exec(open("fpt_prelim/03_simulate.py").read().split('if __name__')[0])
import numpy as np, pandas as pd
main=load("main"); B=eb(main); H=26; hs=[0,6,11,26]
keep=["indicator","label","iso3","country_name","region_name","income_level_name","n_obs","last_obs","women_now","men_now","drift_pp_per_yr","back_delay_D","back_delay_censored"]
res=[]
for thr,name in [("men","reach_mens_2024_level"),("half","close_half_of_2024_gap")]:
    s=sim(B,H,hs,thr=thr).rename(columns={"p_h0":"p_already","p_h6":"p_by_2030","p_h11":"p_by_2035","p_h26":"p_by_2050"})
    s["threshold"]=name; res.append(main[keep].merge(s,on=["indicator","iso3"]))
R=pd.concat(res)
def st(r):
    if r.p_already>=.5: return "already there"
    if r.p_by_2050<.5: return "unlikely by 2050"
    return f"median wait {int(r.median_T)}y"
R["status"]=R.apply(st,axis=1)
R.to_csv("fpt_prelim/fpt_results_final_eb.csv",index=False)
S=R.groupby(["threshold","indicator"]).agg(n=("iso3","size"),already=("p_already",lambda x:(x>=.5).mean()),
   mean_p2030=("p_by_2030","mean"),unlikely_2050=("p_by_2050",lambda x:(x<.5).mean()),median_wait_if_reachable=("median_T","median")).round(2)
print(S.to_string()); S.to_csv("fpt_prelim/fpt_summary_by_indicator.csv")
L=R[(R.indicator=="SL.TLF.CACT.FE.ZS")&(R.threshold=="close_half_of_2024_gap")]
print(L.groupby("region_name").agg(n=("iso3","size"),mean_p2030=("p_by_2030","mean"),share_unlikely=("p_by_2050",lambda x:(x<.5).mean())).round(2).to_string())
print(L.sort_values("women_now")[["country_name","women_now","men_now","drift_pp_per_yr","p_by_2030","p_by_2050","status"]].head(12).round(2).to_string(index=False))
