# How Unevenly Progress Travels — rural vs urban women

Code for the **Measure → Discover → Compare → Explain → Predict** framework in the project
doc (Carolina Data Challenge 2026, Graduate dataset).

> *Two women can be born in the same country and the same year, yet live in different development decades.*

## Run it

```bash
# folder layout (same as Desktop/CDC2026)
#   CDC2026/Graduate_Dataset/all_sources/002_WDI/...   <- data (unchanged)
#   CDC2026/project_code/                               <- this folder
pip install -r requirements.txt
python run_all.py              # ~15 min on a laptop; the Bayesian MCMC is ~9 of them
python run_all.py --from 3     # re-run later steps without refitting the latent model
```
Data are read from `../Graduate_Dataset/all_sources` by default; override with `CDC_DATA=/path/to/all_sources`.
Outputs go to `project_code/outputs/` (override with `CDC_OUT`). Seeds are fixed; runs are reproducible.

| Step | File | Framework stage | What it does |
|---|---|---|---|
| 1 | `s01_build_panel.py` | Measure | Builds the rural women / urban women / rural men / urban men indicator panel (28 indicators, 215 countries, 1990–2024) and validates the rural-women approximation |
| 2 | `s02_latent_model.py` | Measure | Hierarchical Bayesian Dynamic Factor Model (Gibbs sampler + forward-filter backward-sample) → posterior draws of latent opportunity *Z* per group, country, year, for 7 dimensions + Overall. PCA baseline for comparison |
| 3 | `s03_metrics.py` | Discover / Compare | Opportunity Delay, Progress Without Convergence, Inequality Half-Life, Divergence Point, Progress Leakage, Intersectional Penalty, Historical Escapers + DTW analogues — all computed on every posterior draw |
| 4 | `s04_early_warning.py` | Predict | One early-warning model: *will rural women's Opportunity Delay widen in the next 3 years?* Chronological validation with an embargo, plus leave-one-region-out |
| 5 | `s05_evidence_prompts.py` | Explain | Structured LLM evidence-investigation prompts (Finding → Mechanism → Supporting → Contradicting → Confidence); `--run N` queries Claude with web search restricted to World Bank / ILO / UN Women / WHO / UNICEF / FAO / IFAD / UNDP |
| 6 | `s06_report.py` | — | `outputs/country_summary.csv` (one row per country, every headline metric) + 7 figures |

`config.py` holds every choice (indicator map, anchors, years, MCMC length, thresholds). `latent.py` loads posterior draws; `common.py` has loaders and helpers.

## Data: what the sources can and cannot support

**1. Rural *women* are almost never cross-tabulated.** The sources give rural/urban and female/male
marginals separately. The only direct rural-women × urban-women indicators are non-agricultural
employment and the gender wage ratio (086_JON) and two menstrual-health indicators (014_GDS).
Rural-women values are therefore estimated on the log-odds scale:

  logit(RW) = logit(Rural) + logit(Female) − logit(Total)    (years of schooling: additive)

This is **validated** against the one direct measure (non-agricultural employment, 1,263 country-surveys):

| method | MAE | bias | corr |
|---|---|---|---|
| **log-odds (used)** | **0.013** | 0.006 | **0.998** |
| multiplicative | 0.053 | −0.033 | 0.963 |
| rural value only (naive) | 0.090 | −0.044 | 0.903 |
| urban–rural gap for women | 0.019 | −0.011 | 0.994 |

(`outputs/validation_rural_women.csv`). The approximation error is absorbed into each indicator's
measurement variance in the factor model.

**2. Time depth differs by dimension.** Findex / ID4D rural–urban splits exist only for 2017–2024 (mostly 2024).
So Finance, Digital and Resilience are **2024 snapshots**; trajectory metrics (Delay, Half-Life,
Progress Without Convergence) use Education, Employment (JOIN surveys to 2021), Health and Infrastructure
(WHO/UNICEF JMP & SE4ALL, annual). Headline year = **2021**, the last year of the labour/education microdata.

**3. Household-level indicators** (water, sanitation, electricity, cooking fuel) are the same for women and men in an area.

**4. `080_GDL` is empty** — its `_log.csv` shows every indicator returned "not found" from the API.

## Model notes

- Measurement: `y_ict^g ~ N(α_i + λ_i Z_ct^g, σ_i²)`; α, λ, σ shared across the four groups so rural and urban women sit on one scale; λ_i > 0; one anchor indicator per dimension fixes the scale.
- State: `Z_ct^g ~ N(ρ Z_c,t−1^g + δ_c^g + γ_t, τ²)`, `δ_c^g ~ N(μ_region,g, τ_δ²)` (partial pooling across the 6 regions).
- Missing years are simply unobserved; the Kalman recursion bridges survey gaps and widens the posterior where data are thin.
- 10,000 iterations, 4,000 burn-in, thin 30 → 200 draws. Diagnostics in `outputs/latent_model_diagnostics.csv`: split-R̂ ≤ 1.08 for all trajectory dimensions and Overall. Finance's R̂ of 2.1 is on the time-dynamics parameters, which a one-year snapshot cannot inform; its 2024 states converge (R̂ ≈ 1.0). The latent factor agrees with PCA (|r| = 0.87–0.99, except Digital 0.52).
- Anchors: Employment uses non-farm wage employment (employment-to-population loads ≈ 0 because subsistence farming inflates it in poorer countries); Infrastructure uses clean cooking (electricity sits at 100% in most countries and mixed poorly).

## Metric definitions and the decisions behind them

**Opportunity Delay** — `D = argmin_d Σ_k w_k (Z^RW_{t−k} − Z^UW_{t−d−k})²`, K = 5, w_k ∝ 0.85^k, d on a 0.25-year grid, per posterior draw.
When rural women today are below *every* urban-women level since 1990, the delay is **censored**: it is
reported as a lower bound (`delay_is_lower_bound`, shown as ">31"). `delay_ext_*` additionally extrapolates
the urban path linearly before 1990 (explicit assumption, capped at 60) and is what the escaper and
early-warning steps use, so they are not biased by the censoring. `years_to_nearest_obs` flags extrapolated years.

**Progress Without Convergence** — P(ΔZ^RW > 0 and ΔG > 0) over 2000–10, 2005–15, 2010–20, 2015–21.
Labels need ≥ 60% posterior probability ("Uncertain" otherwise), "At parity" when |G| < 0.1 at both ends,
"Insufficient data" when the window lies outside the observed survey span.

**Inequality Half-Life** — hierarchical `log G = a_c − λ_c t + ε`, `λ_c ~ N(μ_region, τ²)`, fitted as a cut posterior
(each Gibbs step sees a fresh posterior draw of G). A half-life is reported only if P(λ_c > 0) ≥ 0.8; otherwise the verdict is
"No strong evidence of convergence" (or "Diverging" if ≤ 0.2).

**Divergence Point** — a change point in the *speed* of the gap (ΔG_t), whose yearly innovations are independent under
the state model. (A broken line on the smooth level G always "finds" a kink; that version was tried and rejected.)
Reports P(a change point exists) via BIC weight, P(τ | data) and the most probable 4-year window.
Run on the annual dimensions (Overall, Health, Infrastructure) only.

**Progress Leakage** — Education → Employment is a hierarchical longitudinal model
`Emp^g_{c,t+3} = a_{c,g} + γ_t + β_{c,g} Edu^g_{c,t} + b·logGDP + ε`, `β_{c,g} ~ N(μ_g, τ²)`, restricted to years inside each
series' observed span; Λ = μ_UW − μ_RW with P(Λ > 0 | data), plus per-country Λ_c.
Employment → Finance, Digital → Finance and Finance → Resilience are 2024 cross-country regressions (the data allow nothing else).

**Intersectional Penalty** — computed **only from the direct rural and urban gender wage ratios**:
`I = G^F − G^M = log(w_UW/w_UM) − log(w_RW/w_RM)`, hierarchical by country and region.
It is *not* computed from the latent index: under the log-odds approximation the rural–urban gap in log-odds is
identical for women and men by construction, so any latent-index version would just restate the assumption.

**Historical Escapers** — country-years with delay ≥ 2 years and a meaningful gap (G ≥ 0.2), classified by D_{t+10}/D_t
(< 0.5 Escaper, 0.5–0.8 Partial, 0.8–1.2 Stagnator, > 1.2 Fall behind); distinguishing characteristics with L2-logistic
(region effects) and LightGBM + SHAP under country-grouped CV. `dtw_analogues.csv` matches each country's last 8 years
of (Z^RW, Z^UW) to historical trajectories with Dynamic Time Warping and reports what happened to those analogues.

**Early warning** — `Y = 1(P(D_{t+3} > D_t | data) > 0.5)`. Features use only information available at *t*
(Kalman-filtered states, not smoothed): delay and its 3-year change, dimension gaps and changes, rural levels, a rolling
Education→Employment conversion gap, and national macro controls. Rows with a gap below 0.2 are dropped.
Train t ≤ 2010 · validate 2013–15 (tuning) · refit on t ≤ 2013 · test 2016–21.

## Results (current run)

**Opportunity Delay, 2021, countries with a meaningful gap**

| dimension | countries | beyond the 1990 record | median delay where measurable |
|---|---|---|---|
| Education | 96 | 5% | 17.0 years |
| Health | 124 | 52% | 11.9 years |
| Infrastructure | 135 | 49% | 15.8 years |
| **Employment** | 97 | **77%** | 21.3 years |
| Overall | 113 | 58% | 19.2 years |

In 89% of countries with both measures, rural women's employment delay exceeds their education delay.
Education largely reached rural women; economic opportunity did not follow at the same speed.
Examples (Overall, 90% CI): India 13.5 (9.5–18.8), Bangladesh 8.8 (5.5–14.8), Kenya 20.1 (14.5–25.3), Ethiopia > 31.

**Progress Without Convergence, 2010–2020 (Overall):** 103 countries converging, 10 flagged
(Belarus, Botswana, Comoros, Djibouti, Liberia, North Macedonia, Nicaragua, Russia, South Sudan, Chad).
Health (36) and Infrastructure (24) show it more often.

**Half-Life (Overall):** 90 of 139 countries show convergence with P ≥ 0.8; the median half-life is ~27 years.
38 show no strong evidence of convergence and 11 are diverging.

**Divergence Point:** the Overall gap moves at a near-constant speed in every country, so there is no discrete divergence point
(partly because the JMP household series are themselves smoothed estimates). Health shows change points in 52 countries
(35 divergence, 17 convergence breaks) and Infrastructure in 62. These are the windows sent to the LLM investigation.

**Progress Leakage:** no evidence that conversion is weaker for rural women on any link. Education → Employment has
Λ = −0.05 (90% CI −0.13 to 0.03), P(Λ > 0) = 0.17, and the cross-sectional links have P = 0.32–0.39.
Read together with the delays, this suggests the gap is structural (levels): rural women's employment starts decades behind,
rather than their gains converting less efficiently.

**Intersectional Penalty (wage ratios, 118 countries):** global P(I > 0) = 0.67; Asia 0.78, Europe 0.73.
There is weak evidence that the gender pay penalty is larger in rural areas. Country-level results split both ways
(40 countries with P > 0.9, 27 with P < 0.1).

**Early warning (test 2016–2021):**

| model | AUC | PR-AUC | Brier |
|---|---|---|---|
| persistence baseline | 0.54 | 0.19 | 0.29 |
| elastic-net logistic | 0.79 | 0.42 | 0.13 |
| **LightGBM** | **0.87** | **0.59** | **0.11** |
| LightGBM, leave-one-region-out | 0.65 | 0.21 | 0.16 |

Highest 2024→2027 risk: Mali, Comoros, Somalia, South Sudan, Malawi, Portugal, Albania, Central African Republic.
The drop under leave-region-out means the model transfers only partly to regions it has not seen.

**Escapers:** after excluding near-parity settings, only 19 escape episodes in 6 countries (Bangladesh, Belarus, Bhutan,
Estonia, Palestine, Thailand), with grouped-CV AUC 0.70. Treat this as exploratory. The strongest signals are a smaller health gap,
a gap already narrowing, and a lower agricultural share.

## Caveats worth stating in the write-up

- Rural-women series are model-based estimates, not direct measurements (validated above, but still an assumption).
- Employment indicators (non-farm, wage, contract) are partly structural: rural economies are agricultural by definition, so part of the employment gap is sectoral composition, not only opportunity.
- Latent units are relative (anchor-indicator SD); delays in years are the interpretable output.
- The early-warning features use filtered states, but the model parameters are estimated on the full sample, which is a mild look-ahead.
- Everything in Escapers / SHAP is associational: *"among historically similar settings, these characteristics distinguished places that later converged"*.

## Outputs

```
outputs/
  panel_long.csv, coverage.csv, validation_rural_women.csv, macro_panel.csv, wage_ratio_panel.csv
  latent/<Dimension>.npz               posterior draws (draws × series × years) + filtered means
  latent_model_diagnostics.csv
  metrics/opportunity_delay.csv        every country × year × dimension, with CI and censoring flags
  metrics/progress_without_convergence.csv, inequality_half_life.csv, divergence_point.csv,
          divergence_posterior_<dim>.csv, progress_leakage.csv, leakage_edu_emp_by_country.csv,
          intersectional_penalty_*.csv, historical_escapers.csv, escaper_characteristics.csv, dtw_analogues.csv
  early_warning/ew_performance.csv, early_warning_2024_to_2027.csv, ew_shap_importance.csv, ...
  evidence/prompts.jsonl               (+ responses.jsonl after --run)
  country_summary.csv                  one row per country, all headline metrics
  figures/fig1 … fig7 .png
```
