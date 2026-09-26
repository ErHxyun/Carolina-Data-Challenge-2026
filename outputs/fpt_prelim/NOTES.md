# Part 1 — First-Passage Time (preliminary, 2026-09-26)

**Question:** starting from 2024, how many years until women's latent level Z reaches a threshold Z*?
T* = inf{h ≥ 0 : Z_{2024+h} ≥ Z*}. Reported as P(T* ≤ 2030 / 2035 / 2050) and the median, labelled "unlikely by 2050" when P(T* ≤ 2050) < 0.5.

## Model (per country × indicator, WDI, fit window 2000–2024)
- Observation: y_t = Z_t + ε_t; state: Z_t = Z_{t-1} + μ + η_t (statsmodels `UnobservedComponents('lldtrend')`, Kalman, missing years handled natively)
- Scale: logit for % indicators, log for gross enrollment/completion; oriented so higher = better (vulnerable employment is flipped)
- Thresholds: (a) men's latent 2024 level (with its uncertainty); (b) closing half of the 2024 gap
- Simulation: 4,000 paths drawn from the terminal (level, drift) distribution + future shocks
- Drift shrinkage: empirical-Bayes partial pooling of μ within indicator × income group (`03_simulate.py: eb`)
- Also computed: backward delay D = years since men's smoothed level equalled women's current level

## Indicators
SL.TLF.CACT (LFPR 15+), SL.EMP.WORK (wage & salaried), SL.EMP.VULN (vulnerable employment), SE.SEC.CMPT.LO (lower secondary completion), SE.TER.ENRR (tertiary GER), FX.OWN.TOTL (account ownership)

## Headline results (`fpt_summary_by_indicator.csv`)
- Education is mostly at parity already (tertiary: 85% of economies; lower secondary: about 75%).
- **Labour force participation is the binding constraint:** 96% of economies are unlikely to reach men's 2024 LFPR by 2050, and 80% are unlikely even to close half the gap. MENA is the extreme case: flat or negative drift at 5–20% LFPR.
- Account ownership is moving fast (median about 3 years to reach men's level) but rests on only about 4 Findex waves, so treat it with caution.

## Backtest (fit to 2012 / 2016, check realised 2024) — `backtest_*.csv`
- Overall Brier skill vs climatology: 0.10–0.20 (EB beats the plug-in version).
- **Overconfident:** cases given p ≥ 0.8 were realised only about 55–64% of the time.
- Education series (sparse, survey-cycle) are badly calibrated (negative BSS). The ILO labour series do better, but they are themselves modelled estimates, so this validation is partly circular.

## Caveats / next steps
1. Parameter uncertainty is ignored (plug-in MLE variances). Next: a full Bayesian fit (PyMC/NumPyro) with a hierarchical drift across countries, which is also the natural fix for the overconfidence.
2. Move from single indicators to the latent multi-indicator Z (dynamic factor measurement model). The poor education calibration argues for pooling noisy indicators.
3. ILO modelled series include projections to 2025. They are truncated at 2024, but earlier years still embed ILO model smoothing.
4. Rural/urban splits are not in WDI. They need GDS/HNP/Findex sources once those downloads finish.
5. Mixed thresholds: for "half the gap", "already there" means women are already ahead.

## Files
00_coverage.py → fe_ma_pair_coverage.csv (all FE/MA pairs in WDI)
01_fpt.py → per-indicator Kalman fits and plug-in FPT (`fpt_results_<tag>_part*.csv`)
02/03/03b → backtests (plug-in vs EB; men's-level and half-gap thresholds)
04_final.py → **fpt_results_final_eb.csv** (country-level) and fpt_summary_by_indicator.csv
