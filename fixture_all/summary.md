# Evidence agent run - fixture backend

Evidence reports contextualize statistical signals. **None asserts causality** (`causal_conclusion` is always `false`). Confidence rates the contextual evidence, not the probability that a mechanism caused the signal.

- Backend: `fixture`; source inspection: `True`
- Tasks: 35 - abstained: 29, completed: 6
- Overall confidence: insufficient: 29, low: 3, medium: 3
- Flagged for mandatory human review: 34

| Task | Country | Trigger | Disposition | Overall | Leading mechanism | Review flags |
|---|---|---|---|---|---|---|
| CONV-D-001 | Yemen, Rep. | education_progress_without_employment_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-D-002 | West Bank and Gaza | education_progress_without_employment_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-D-003 | Cambodia | education_progress_without_employment_conversion | completed | low | unpaid_care | low_or_insufficient_confidence |
| CONV-D-004 | Sierra Leone | education_progress_without_employment_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-D-005 | Bhutan | education_progress_without_employment_conversion | completed | medium | unpaid_care |  |
| CONV-D-006 | Guinea | education_progress_without_employment_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-D-007 | Iraq | education_progress_without_employment_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-D-008 | Cameroon | education_progress_without_employment_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-D-009 | Kyrgyz Republic | education_progress_without_employment_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-D-010 | Burkina Faso | education_progress_without_employment_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-P-001 | Togo | positive_converter | completed | low | broad_participation | low_or_insufficient_confidence, politically_or_legally_sensitive_claim, source_reused_not_independent |
| CONV-P-002 | Turkmenistan | positive_converter | abstained | insufficient | - | low_or_insufficient_confidence, positive_converter_job_quality_unverified |
| CONV-P-003 | Azerbaijan | positive_converter | abstained | insufficient | - | low_or_insufficient_confidence, positive_converter_job_quality_unverified |
| CONV-P-004 | Mozambique | positive_converter | completed | low | broad_participation | annotated_time_match_inconsistent_with_publication_year, low_or_insufficient_confidence, reviewed_claim_corrected_after_source_check |
| CONV-P-005 | Congo, Dem. Rep. | positive_converter | abstained | insufficient | - | low_or_insufficient_confidence, positive_converter_job_quality_unverified |
| CONV-P-006 | Nigeria | positive_converter | abstained | insufficient | - | low_or_insufficient_confidence, positive_converter_job_quality_unverified |
| CONV-P-007 | South Sudan | positive_converter | abstained | insufficient | - | low_or_insufficient_confidence, positive_converter_job_quality_unverified |
| CONV-P-008 | Sierra Leone | positive_converter | abstained | insufficient | - | low_or_insufficient_confidence, positive_converter_job_quality_unverified |
| CONV-P-009 | Puerto Rico (US) | positive_converter | abstained | insufficient | - | low_or_insufficient_confidence, positive_converter_job_quality_unverified |
| CONV-P-010 | Angola | positive_converter | abstained | insufficient | - | low_or_insufficient_confidence, positive_converter_job_quality_unverified |
| CONV-U-001 | Oman | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-002 | Afghanistan | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-003 | Egypt, Arab Rep. | persistent_under_conversion | completed | medium | unpaid_care | annotated_time_match_inconsistent_with_publication_year, cited_title_not_found_in_document, source_reused_not_independent |
| CONV-U-004 | Iraq | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-005 | Saudi Arabia | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-006 | Yemen, Rep. | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-007 | West Bank and Gaza | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-008 | India | persistent_under_conversion | completed | medium | unpaid_care | cited_title_not_found_in_document, retrieved_evidence_rejected |
| CONV-U-009 | Sudan | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-010 | Bahrain | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-011 | Iran, Islamic Rep. | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-012 | Fiji | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-013 | United Arab Emirates | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-014 | Syrian Arab Republic | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |
| CONV-U-015 | Mauritania | persistent_under_conversion | abstained | insufficient | - | low_or_insufficient_confidence |

## CONV-D-003 - Cambodia (completed, overall low)

**1. What the model found.** Between 2000 and 2024, Cambodia's education gender gap improved by 0.63 SD, while its employment gender gap improved by only -0.13 SD between 2000 and 2024. The descriptive conversion shortfall is 0.77 SD. *Period:* 2000-2024 (window [2000, 2024]). *Uncertainty:* This signal is descriptive and model-dependent. It is not proof of a policy mechanism or causal effect. The divergence compares endpoint changes in country-level indicators that may cover different cohorts, reference years, age groups and surveys; it is not a longitudinal estimate for the same women.

**2-3. What sources document, and the inferred plausible connection.**
- *Unpaid care work and limited childcare is a plausible mechanism that may help contextualize Cambodia's divergence between its education and employment gender-gap trajectories.* - confidence **low**. Low: 1 distinct source(s) from 1 organization(s) (World Bank); 1 from tier 1-3 institutions; 1 of 1 temporally aligned with 2000-2024 (0 with the period stated in the source); no independent corroboration; no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *Cambodia Community-Based Childcare for Garment Factory Workers Project — Implementation Completion and Results Report* (2024)](https://documents1.worldbank.org/curated/en/099093024201032461/pdf/P1710631889fc6041a6d911a25a5ac4729.pdf) - time: **during** - The project completion report states that women perform about 90 percent of unpaid care, that childbirth is associated with labor-market exit and that childcare access is limited.
- *Skills mismatch is a plausible mechanism that may help contextualize Cambodia's divergence between its education and employment gender-gap trajectories.* - confidence **low**. Low: 1 distinct source(s) from 1 organization(s) (International Labour Organization); 1 from tier 1-3 institutions; 1 of 1 temporally aligned with 2000-2024 (0 with the period stated in the source); no independent corroboration; sources do not directly address women's paid work; no source estimates this mechanism's contribution to the modeled signal.
  - [International Labour Organization, *Cambodia: Addressing the skills gap — Employment diagnostic study* (2015)](https://www.ilo.org/publications/cambodia-addressing-skills-gap-employment-diagnostic-study) - time: **during** - The employment diagnostic describes high participation and low unemployment alongside pervasive informality, low education, a narrow economic base and skills mismatch. **[CHECK: page content not machine-checkable (dynamic page)]**
- *Occupational and sectoral segregation is a plausible mechanism that may help contextualize Cambodia's divergence between its education and employment gender-gap trajectories.* - confidence **low**. Low: 1 distinct source(s) from 1 organization(s) (World Bank); 1 from tier 1-3 institutions; 1 of 1 temporally aligned with 2000-2024 (0 with the period stated in the source); no independent corroboration; sources do not directly address women's paid work; complicating evidence addresses the same mechanism; no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *Cambodia Skills for Better Jobs* (2023)](https://documents1.worldbank.org/curated/en/099080823003040193/pdf/P1791590b50c330508d11084f55d7a843a.pdf) - time: **during** - The skills report describes women's concentration in low-skill manufacturing and services, limited advancement, care constraints and gender norms.

**Contradicting or complicating evidence.**
  - [International Labour Organization, *Cambodia Garment and Footwear Sector Bulletin, Issue 8* (2019)](https://www.ilo.org/publications/cambodia-garment-and-footwear-sector-bulletin-issue-8-december-2018) - time: **during** - Cambodia's garment and footwear sector supported roughly one million jobs, around four-fifths held by women, providing regular employment and income despite a gender pay gap.

**4. What remains unknown / limitations.**
- The divergence compares country-level indicator trajectories that may refer to different cohorts, reference years, age groups and surveys; it does not show that the same women gained education and then failed to find work.
- 1 complicating source(s) document vulnerable, informal, own-account or unpaid work; changes in measured participation may not represent gains in paid, secure or advancing employment.
- National figures can mask differences by rurality, age, income, disability, ethnicity and region; none of the cited sources isolates the sub-population behind the signal.
- The available sources do not establish causality; mechanisms are plausible context, not explanations of the statistical signal.
- Evidence was served from an offline fixture derived from reviewed pilot reports; it was not independently re-retrieved by live search.
- Not found: S1: Do authoritative sources document difficult school-to-work transitions limiting how women's educational gains in Cambodia became paid employment over 2000-2024, and does the evidence refer to the same age groups or cohorts?
- Not found: S3: Do authoritative sources document shortage of suitable, secure or acceptable jobs limiting how women's educational gains in Cambodia became paid employment over 2000-2024, and does the evidence refer to the same age groups or cohorts?
- Not found: S6: Do authoritative sources document reliance on a shrinking public-sector employment pathway limiting how women's educational gains in Cambodia became paid employment over 2000-2024, and does the evidence refer to the same age groups or cohorts?
- Not found: A causal decomposition attributing the country's signal to specific mechanisms.

Review flags: `fixture_evidence_not_live_retrieved, low_or_insufficient_confidence`

## CONV-D-005 - Bhutan (completed, overall medium)

**1. What the model found.** Between 2000 and 2024, Bhutan's education gender gap improved by 0.69 SD, while its employment gender gap improved by only 0.01 SD between 2000 and 2024. The descriptive conversion shortfall is 0.68 SD. *Period:* 2000-2024 (window [2000, 2024]). *Uncertainty:* This signal is descriptive and model-dependent. It is not proof of a policy mechanism or causal effect. The divergence compares endpoint changes in country-level indicators that may cover different cohorts, reference years, age groups and surveys; it is not a longitudinal estimate for the same women.

**2-3. What sources document, and the inferred plausible connection.**
- *Unpaid care work and limited childcare is a plausible mechanism that may help contextualize Bhutan's divergence between its education and employment gender-gap trajectories.* - confidence **medium**. Medium: 2 distinct source(s) from 1 organization(s) (World Bank); 2 from tier 1-3 institutions; 2 of 2 temporally aligned with 2000-2024 (0 with the period stated in the source); no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *Fostering Childcare to Enable Female Labor Force Participation in Bhutan* (2024)](https://blogs.worldbank.org/en/endpovertyinsouthasia/fostering-childcare-to-enable-female-labor-force-participation-i) - time: **during** - The feature reports a persistent participation gap, disproportionate childcare constraints and limited receipt of maternity benefits among new mothers.
  - [World Bank, *Bhutan Gender Policy Note* (2013)](https://documents1.worldbank.org/curated/en/960591468017989867/pdf/ACS45510PNT0P10Box0379884B00PUBLIC0.pdf) - time: **during** - The country gender policy report finds improvement in female participation but persistent job-quality and earnings gaps associated with education endowments, occupational segregation, household chores and childcare.
- *Reliance on a shrinking public-sector employment pathway is a plausible mechanism that may help contextualize Bhutan's divergence between its education and employment gender-gap trajectories.* - confidence **low**. Low: 1 distinct source(s) from 1 organization(s) (World Bank); 1 from tier 1-3 institutions; 1 of 1 temporally aligned with 2000-2024 (0 with the period stated in the source); no independent corroboration; no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *A Strong Labor Market Is Key to Bhutan’s Inclusive Growth* (2024)](https://www.worldbank.org/en/news/feature/2024/03/11/a-strong-labor-market-is-key-to-bhutan-s-inclusive-growth) - time: **during** - The labor-market assessment describes segmentation by gender, location and education, concentration of women and rural workers in low-productivity agriculture, elevated NEET risk for young women and queuing for public-sector jobs among educated workers.

**Contradicting or complicating evidence.**
  - [World Bank, *Bhutan Gender Data Landscape* (2022)](https://documents1.worldbank.org/curated/en/099502206242210197/pdf/IDU12f89089c170d814a7d1b2ef155431ac8ff82.pdf) - time: **during** - The gender data landscape reports female lower-secondary completion above male completion, while female participation remains below male participation and vulnerable employment remains high for both sexes.
  - [World Bank, *Bhutan Country Gender Profile* (2016)](https://documents1.worldbank.org/curated/en/566161487277272050/pdf/112879-WP-PUBLIC-June-2016-SARRGAPFYUpdatedFYQfinal.pdf) - time: **during** - An earlier country profile documented rapid movement toward education parity and noted that some young female cohorts had relatively stronger participation than older women.

**4. What remains unknown / limitations.**
- The divergence compares country-level indicator trajectories that may refer to different cohorts, reference years, age groups and surveys; it does not show that the same women gained education and then failed to find work.
- 1 complicating source(s) document vulnerable, informal, own-account or unpaid work; changes in measured participation may not represent gains in paid, secure or advancing employment.
- National figures can mask differences by rurality, age, income, disability, ethnicity and region; none of the cited sources isolates the sub-population behind the signal.
- The available sources do not establish causality; mechanisms are plausible context, not explanations of the statistical signal.
- Evidence was served from an offline fixture derived from reviewed pilot reports; it was not independently re-retrieved by live search.
- Not found: S1: Do authoritative sources document difficult school-to-work transitions limiting how women's educational gains in Bhutan became paid employment over 2000-2024, and does the evidence refer to the same age groups or cohorts?
- Not found: S2: Do authoritative sources document skills mismatch limiting how women's educational gains in Bhutan became paid employment over 2000-2024, and does the evidence refer to the same age groups or cohorts?
- Not found: S3: Do authoritative sources document shortage of suitable, secure or acceptable jobs limiting how women's educational gains in Bhutan became paid employment over 2000-2024, and does the evidence refer to the same age groups or cohorts?
- Not found: A causal decomposition attributing the country's signal to specific mechanisms.

Review flags: `fixture_evidence_not_live_retrieved`

## CONV-P-001 - Togo (completed, overall low)

**1. What the model found.** Togo's latest female employment-opportunity score is -0.25 SD relative to men, compared with an out-of-fold expected value of -1.32 SD. The positive residual is 1.07 SD (approximately the upper 1% tail), suggesting stronger conversion than comparable observations. *Period:* Latest available observations through 2024 (window [2017, 2024]). *Uncertainty:* This signal is descriptive and model-dependent. It is not proof of a policy mechanism or causal effect. A positive residual is not evidence of success: higher-than-predicted employment access can coexist with vulnerable, informal, unpaid, low-paid or insecure work. Predictor observations mix survey years; see indicator years.

**2-3. What sources document, and the inferred plausible connection.**
- *Broad, often necessity-driven, female labor-force participation may help contextualize Togo's higher-than-predicted employment-access outcome; participation alone does not indicate job quality or empowerment.* - confidence **low**. Low: 1 distinct source(s) from 1 organization(s) (World Bank); 1 from tier 1-3 institutions; 1 of 1 temporally aligned with 2017-2024 (0 with the period stated in the source); no independent corroboration; no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *Togo Gender Data Landscape* (2022)](https://documents1.worldbank.org/curated/en/099930107032270670/pdf/IDU023e151a3048ea046610937c02e7924f61b47.pdf) - time: **during** - The country gender landscape reports near parity in female and male labor-force participation in its latest estimate.
- *Informality and vulnerable employment is a plausible feature of Togo's labor market that may mean its higher-than-predicted employment-access outcome coexists with weak job quality.* - confidence **low**. Low: 1 distinct source(s) from 1 organization(s) (World Bank); 1 from tier 1-3 institutions; 1 of 1 temporally aligned with 2017-2024 (0 with the period stated in the source); no independent corroboration; no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *Togo Gender Data Landscape* (2022)](https://documents1.worldbank.org/curated/en/099930107032270670/pdf/IDU023e151a3048ea046610937c02e7924f61b47.pdf) - time: **during** - The same landscape reports substantially higher vulnerable employment among women than men and large gender gaps in account ownership, internet use and land ownership.

**Contradicting or complicating evidence.**
  - [World Bank, *Women, Business and the Law 2010* (2010)](https://wbl.worldbank.org/content/dam/sites/wbl/documents/2021/02/WBL2010.pdf) - time: **before** - Historical legal indicators documented inequalities in property, inheritance and aspects of women's legal capacity despite substantial female labor-force participation.

**4. What remains unknown / limitations.**
- A higher-than-predicted employment-access score is not evidence of success or empowerment: participation can coexist with vulnerable, informal, unpaid, low-paid or insecure work.
- National figures can mask differences by rurality, age, income, disability, ethnicity and region; none of the cited sources isolates the sub-population behind the signal.
- The available sources do not establish causality; mechanisms are plausible context, not explanations of the statistical signal.
- Evidence was served from an offline fixture derived from reviewed pilot reports; it was not independently re-retrieved by live search.
- Not found: S3: Do authoritative sources document unpaid family work in Togo during or shortly before 2017-2024, and does it indicate whether women's higher-than-predicted employment access reflects secure, paid work?
- Not found: S4: Do authoritative sources document wage gaps and limited career advancement in Togo during or shortly before 2017-2024, and does it indicate whether women's higher-than-predicted employment access reflects secure, paid work?
- Not found: S5: Do authoritative sources document occupational and sectoral segregation in Togo during or shortly before 2017-2024, and does it indicate whether women's higher-than-predicted employment access reflects secure, paid work?
- Not found: A causal decomposition attributing the country's signal to specific mechanisms.

Review flags: `fixture_evidence_not_live_retrieved, low_or_insufficient_confidence, politically_or_legally_sensitive_claim, source_reused_not_independent`

## CONV-P-004 - Mozambique (completed, overall low)

**1. What the model found.** Mozambique's latest female employment-opportunity score is -0.29 SD relative to men, compared with an out-of-fold expected value of -1.07 SD. The positive residual is 0.78 SD (approximately the upper 2% tail), suggesting stronger conversion than comparable observations. *Period:* Latest available observations through 2024 (window [2017, 2024]). *Uncertainty:* This signal is descriptive and model-dependent. It is not proof of a policy mechanism or causal effect. A positive residual is not evidence of success: higher-than-predicted employment access can coexist with vulnerable, informal, unpaid, low-paid or insecure work. Predictor observations mix survey years; see indicator years.

**2-3. What sources document, and the inferred plausible connection.**
- *Broad, often necessity-driven, female labor-force participation may help contextualize Mozambique's higher-than-predicted employment-access outcome; participation alone does not indicate job quality or empowerment.* - confidence **low**. Low: 1 distinct source(s) from 1 organization(s) (World Bank); 1 from tier 1-3 institutions; 1 of 1 temporally aligned with 2017-2024 (0 with the period stated in the source); no independent corroboration; no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *Mozambique Women Economic Empowerment Project Annex* (2022)](https://documents1.worldbank.org/curated/en/099840008042230800/pdf/BOSIB06a21fb800430ac95087a2dee12798.pdf) - time: **during** - A World Bank project annex reports female and male labor-force participation at 78 and 79 percent in 2021, while also noting continued gender gaps in management and sectoral concentration.
- *Informality and vulnerable employment is a plausible feature of Mozambique's labor market that may mean its higher-than-predicted employment-access outcome coexists with weak job quality.* - confidence **low**. Low: 1 distinct source(s) from 1 organization(s) (International Labour Organization); 1 from tier 1-3 institutions; 1 of 1 temporally aligned with 2017-2024 (0 with the period stated in the source); no independent corroboration; complicating evidence addresses the same mechanism; no source estimates this mechanism's contribution to the modeled signal.
  - [International Labour Organization, *Enabling Environment for Women in Growth Enterprises in Mozambique* (2011)](https://www.ilo.org/publications/enabling-environment-women-growth-enterprises-mozambique) - time: **before** - The assessment reports that women entrepreneurs face barriers and are overrepresented in microenterprises, low-growth sectors and the informal economy. **[CHECK: page content not machine-checkable (dynamic page)]**

**Contradicting or complicating evidence.**
  - [UN Women and International Labour Organization, *Fiscal policy and gender equality: Mozambique country report* (2024)](https://www.ilo.org/sites/default/files/2024-07/UNWomen-ILO%20Consolidated%20report_Fiscal_Final_Edited%20Jan%2024.pdf) - time: **during** - A UN Women-ILO multi-country fiscal-policy report's Mozambique section states that most pandemic-response measures were not gender-responsive, that the workforce is primarily rural with 72.8 per cent in agriculture and the informal sector, and that women are overrepresented in the informal sector that the implemented programmes excluded.
  - [World Bank, *A Girl Can Dream: Analyzing Aspirations, Gender Norms, and Influencers among Girls and Women in Mozambique* (2023)](https://www.worldbank.org/en/country/mozambique/publication/a-girl-can-dream-analyzing-aspirations-gender-norms-and-influencers-among-girls-and-women-in-mozambique) - time: **during** - Research on girls' and women's aspirations finds that desired occupations are not always aligned with sectors able to absorb workers and highlights norms, family gatekeeping and financial constraints.

**4. What remains unknown / limitations.**
- A higher-than-predicted employment-access score is not evidence of success or empowerment: participation can coexist with vulnerable, informal, unpaid, low-paid or insecure work.
- 1 complicating source(s) document vulnerable, informal, own-account or unpaid work; changes in measured participation may not represent gains in paid, secure or advancing employment.
- National figures can mask differences by rurality, age, income, disability, ethnicity and region; none of the cited sources isolates the sub-population behind the signal.
- The available sources do not establish causality; mechanisms are plausible context, not explanations of the statistical signal.
- Evidence was served from an offline fixture derived from reviewed pilot reports; it was not independently re-retrieved by live search.
- Not found: S3: Do authoritative sources document unpaid family work in Mozambique during or shortly before 2017-2024, and does it indicate whether women's higher-than-predicted employment access reflects secure, paid work?
- Not found: S6: Do authoritative sources document limited financial inclusion and account ownership in Mozambique during or shortly before 2017-2024, and does it indicate whether women's higher-than-predicted employment access reflects secure, paid work?
- Not found: A causal decomposition attributing the country's signal to specific mechanisms.

Review flags: `annotated_time_match_inconsistent_with_publication_year, fixture_evidence_not_live_retrieved, low_or_insufficient_confidence, reviewed_claim_corrected_after_source_check`

## CONV-U-003 - Egypt, Arab Rep. (completed, overall medium)

**1. What the model found.** Egypt, Arab Rep.'s latest female employment-opportunity score is -1.98 SD relative to men. A cross-validated model using education, financial inclusion, digital inclusion and macro conditions expected -0.70 SD. The out-of-fold residual is -1.28 SD (lower 2% of countries), indicating under-conversion relative to comparable observations. *Period:* Latest available observations through 2024 (window [2022, 2024]). *Uncertainty:* This signal is descriptive and model-dependent. It is not proof of a policy mechanism or causal effect. The residual is an out-of-fold model residual, not a causal effect or a confidence interval; it can arise from omitted predictors or measurement error. Predictor observations mix survey years; see indicator years.

**2-3. What sources document, and the inferred plausible connection.**
- *Unpaid care work and limited childcare is a plausible mechanism that may help contextualize Egypt, Arab Rep.'s lower-than-predicted female employment-opportunity outcome.* - confidence **medium**. Medium: 2 distinct source(s) from 2 organization(s) (International Labour Organization, World Bank); 2 from tier 1-3 institutions; 2 of 2 temporally aligned with 2022-2024 (0 with the period stated in the source); complicating evidence addresses the same mechanism; no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *Egypt: Women Economic Empowerment Study* (2019)](https://www.worldbank.org/en/country/egypt/publication/egypt-women-economic-empowerment-study) - time: **before** - The study identifies household responsibilities and difficulty reconciling work and marriage as constraints on women's economic participation. **[CHECK: page content not machine-checkable (dynamic page)]**
  - [International Labour Organization, *Study Report: Business Case for Employer Supported Child Care in Egypt* (2022)](https://www.ilo.org/publications/study-report-business-case-employer-supported-child-care-egypt-childcare) - time: **during** - The report examines employer-supported childcare as a labor-market intervention in Egypt and sets out the business case for expanding it. **[CHECK: page content not machine-checkable (dynamic page)]**
- *Shortage of suitable, secure or acceptable jobs is a plausible mechanism that may help contextualize Egypt, Arab Rep.'s lower-than-predicted female employment-opportunity outcome.* - confidence **medium**. Medium: 2 distinct source(s) from 1 organization(s) (World Bank); 2 from tier 1-3 institutions; 1 of 2 temporally aligned with 2022-2024 (0 with the period stated in the source); no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *Breaking Barriers: Boosting Women’s Labor Force Participation in Egypt* (2025)](https://www.worldbank.org/en/news/feature/2025/03/12/breaking-barriers-boosting-women-s-labor-force-participation-in-egypt) - time: **after** - The feature reports low female labor-force participation and identifies declining agricultural and public-sector jobs, limited private investment, unsafe transport and restrictive norms among the barriers.
  - [World Bank, *Egypt Supporting Egypt Education to Employment Transition* (2022)](https://documents1.worldbank.org/curated/en/099556408032227795/pdf/IDU04351d87c09e470446808cc90004c6187c47a.pdf) - time: **during** - The World Bank project document states that women's education rose while labor-force participation and employment fell, and describes limited access to employment and restrictive gender norms. **[CHECK: cited title not found in the linked document (document reads: 'World Bank Document')]**

**Contradicting or complicating evidence.**
  - [World Bank, *Breaking Barriers: Boosting Women’s Labor Force Participation in Egypt* (2025)](https://www.worldbank.org/en/news/feature/2025/03/12/breaking-barriers-boosting-women-s-labor-force-participation-in-egypt) - time: **after** - Recent government and development-partner programs include cash transfers, employment services, childcare and private-sector initiatives, so the latest policy environment is not uniformly deteriorating.

**4. What remains unknown / limitations.**
- The signal is an out-of-fold residual from an exploratory cross-sectional model; it may reflect predictors missing from the model or measurement error as well as country conditions.
- National figures can mask differences by rurality, age, income, disability, ethnicity and region; none of the cited sources isolates the sub-population behind the signal.
- The available sources do not establish causality; mechanisms are plausible context, not explanations of the statistical signal.
- Evidence was served from an offline fixture derived from reviewed pilot reports; it was not independently re-retrieved by live search.
- Not found: S4: Do authoritative sources document occupational and sectoral segregation constraining women's paid employment in Egypt, Arab Rep. during or shortly before 2022-2024, specifically among women with secondary or tertiary education?
- Not found: S5: Do authoritative sources document legal constraints (family, property, inheritance or labor law) constraining women's paid employment in Egypt, Arab Rep. during or shortly before 2022-2024, specifically among women with secondary or tertiary education?
- Not found: A causal decomposition attributing the country's signal to specific mechanisms.

Review flags: `annotated_time_match_inconsistent_with_publication_year, cited_title_not_found_in_document, fixture_evidence_not_live_retrieved, source_reused_not_independent`

## CONV-U-008 - India (completed, overall medium)

**1. What the model found.** India's latest female employment-opportunity score is -1.38 SD relative to men. A cross-validated model using education, financial inclusion, digital inclusion and macro conditions expected -0.41 SD. The out-of-fold residual is -0.98 SD (lower 5% of countries), indicating under-conversion relative to comparable observations. *Period:* Latest available observations through 2024 (window [2018, 2024]). *Uncertainty:* This signal is descriptive and model-dependent. It is not proof of a policy mechanism or causal effect. The residual is an out-of-fold model residual, not a causal effect or a confidence interval; it can arise from omitted predictors or measurement error. Predictor observations mix survey years; see indicator years.

**2-3. What sources document, and the inferred plausible connection.**
- *Unpaid care work and limited childcare is a plausible mechanism that may help contextualize India's lower-than-predicted female employment-opportunity outcome.* - confidence **medium**. Medium: 2 distinct source(s) from 2 organization(s) (International Labour Organization, World Bank); 2 from tier 1-3 institutions; 2 of 2 temporally aligned with 2018-2024 (1 with the period stated in the source); no source estimates this mechanism's contribution to the modeled signal.
  - [World Bank, *India Gender Portfolio Review* (2017)](https://documents1.worldbank.org/curated/en/377711511422588789/pdf/Main-Report.pdf) - time: **during** - The gender assessment notes that education expansion coincided with declining female labor-force participation and discusses norms, childcare and the limited reach of formal-sector protections. **[CHECK: cited title not found in the linked document (document reads: 'World Bank Document')]**
  - [International Labour Organization, *Young persons not in employment and education in India: 2000–2019* (2020)](https://www.ilo.org/publications/young-persons-not-employment-and-education-india-2000-2019) - time: **during** - The report finds that female NEET status outside the labor force is dominated by household reproduction and care work.

**Contradicting or complicating evidence.**
  - [International Labour Organization, *India Employment Report 2024: Youth employment, education and skills* (2024)](https://www.ilo.org/sites/default/files/2024-08/India%20Employment%20-%20web_8%20April.pdf) - time: **during** - Female labor-force participation rose substantially after 2019, although much of the increase was in self-employment and unpaid family work.
  - [World Bank, *India — Gender Data Portal* (2025)](https://genderdata.worldbank.org/en/economies/india) - time: **after** - The Gender Data Portal reports recent female labor-force participation near one-third, but also high vulnerable employment and a large remaining gap with men. **[CHECK: page content not machine-checkable (dynamic page)]**

**4. What remains unknown / limitations.**
- The signal is an out-of-fold residual from an exploratory cross-sectional model; it may reflect predictors missing from the model or measurement error as well as country conditions.
- 2 complicating source(s) document vulnerable, informal, own-account or unpaid work; changes in measured participation may not represent gains in paid, secure or advancing employment.
- National figures can mask differences by rurality, age, income, disability, ethnicity and region; none of the cited sources isolates the sub-population behind the signal.
- The available sources do not establish causality; mechanisms are plausible context, not explanations of the statistical signal.
- Evidence was served from an offline fixture derived from reviewed pilot reports; it was not independently re-retrieved by live search.
- Not found: S2: Do authoritative sources document shortage of suitable, secure or acceptable jobs constraining women's paid employment in India during or shortly before 2018-2024, specifically among women with secondary or tertiary education?
- Not found: S3: Do authoritative sources document reliance on a shrinking public-sector employment pathway constraining women's paid employment in India during or shortly before 2018-2024, specifically among women with secondary or tertiary education?
- Not found: S4: Do authoritative sources document occupational and sectoral segregation constraining women's paid employment in India during or shortly before 2018-2024, specifically among women with secondary or tertiary education?
- Not found: S5: Do authoritative sources document legal constraints (family, property, inheritance or labor law) constraining women's paid employment in India during or shortly before 2018-2024, specifically among women with secondary or tertiary education?
- Not found: S6: Do authoritative sources document transport access and safety constraining women's paid employment in India during or shortly before 2018-2024, specifically among women with secondary or tertiary education?
- Not found: A causal decomposition attributing the country's signal to specific mechanisms.

**Retrieved but rejected sources.**
- https://documents1.worldbank.org/curated/en/099122425090534097/pdf/BOSIB-974f863f-adc1-4b78-934d-d52add12c2b6.pdf - neither the cited title nor the claim's figures occur in the linked document (probable wrong URL)

Review flags: `cited_title_not_found_in_document, fixture_evidence_not_live_retrieved, retrieved_evidence_rejected`
