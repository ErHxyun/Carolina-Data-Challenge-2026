import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "conversion_evidence_agent"
TASKS = OUT / "conversion_evidence_prompts.jsonl"
SCHEMA = OUT / "conversion_evidence_report_schema.json"
REPORTS = OUT / "pilot_evidence_reports.jsonl"
SUMMARY = OUT / "pilot_evidence_summary.md"
AUDIT = OUT / "pilot_evidence_validation.json"


def evidence(claim, organization, title, year, url, relevance, time_match):
    return {
        "claim": claim,
        "organization": organization,
        "title": title,
        "publication_year": year,
        "url": url,
        "relevance": relevance,
        "time_match": time_match,
    }


task_by_id = {}
for line in TASKS.read_text().splitlines():
    task = json.loads(line)
    task_by_id[task["task_id"]] = task


curated = {
    "CONV-U-003": {
        "mechanisms": [
            {
                "mechanism": "Unpaid care and limited affordable childcare may raise the cost of converting education into sustained paid work.",
                "supporting_evidence": [
                    evidence(
                        "The study identifies household responsibilities and difficulty reconciling work and marriage as constraints on women's economic participation.",
                        "World Bank",
                        "Egypt: Women Economic Empowerment Study",
                        2019,
                        "https://www.worldbank.org/en/country/egypt/publication/egypt-women-economic-empowerment-study",
                        "Directly documents a care-and-household channel relevant to education-to-employment conversion.",
                        "during",
                    ),
                    evidence(
                        "The report examines employer-supported childcare as a labor-market intervention in Egypt and sets out the business case for expanding it.",
                        "International Labour Organization",
                        "Study Report: Business Case for Employer Supported Child Care in Egypt",
                        2022,
                        "https://www.ilo.org/publications/study-report-business-case-employer-supported-child-care-egypt-childcare",
                        "Supports the institutional relevance of childcare constraints without estimating their contribution to this residual.",
                        "during",
                    ),
                ],
                "confidence": "medium",
                "confidence_reason": "Two institutional sources identify the channel, but neither isolates its causal contribution to the modeled country residual.",
            },
            {
                "mechanism": "A shrinking public-sector pathway, weak private job creation, occupational concentration and transport constraints may limit suitable jobs for educated women.",
                "supporting_evidence": [
                    evidence(
                        "The feature reports low female labor-force participation and identifies declining agricultural and public-sector jobs, limited private investment, unsafe transport and restrictive norms among the barriers.",
                        "World Bank",
                        "Breaking Barriers: Boosting Women’s Labor Force Participation in Egypt",
                        2025,
                        "https://www.worldbank.org/en/news/feature/2025/03/12/breaking-barriers-boosting-women-s-labor-force-participation-in-egypt",
                        "Provides a multi-channel institutional account that matches the type of under-conversion signaled by the model.",
                        "after",
                    ),
                    evidence(
                        "The World Bank project document states that women's education rose while labor-force participation and employment fell, and describes limited access to employment and restrictive gender norms.",
                        "World Bank",
                        "Egypt Supporting Egypt Education to Employment Transition",
                        2022,
                        "https://documents1.worldbank.org/curated/en/099556408032227795/pdf/IDU04351d87c09e470446808cc90004c6187c47a.pdf",
                        "Directly frames the education-employment disconnect and documents candidate constraints during the observation window.",
                        "during",
                    ),
                ],
                "confidence": "medium",
                "confidence_reason": "The sources align closely with the signal, but describe several intertwined constraints and do not identify one dominant mechanism.",
            },
        ],
        "contradicting_or_complicating_evidence": [
            evidence(
                "Recent government and development-partner programs include cash transfers, employment services, childcare and private-sector initiatives, so the latest policy environment is not uniformly deteriorating.",
                "World Bank",
                "Breaking Barriers: Boosting Women’s Labor Force Participation in Egypt",
                2025,
                "https://www.worldbank.org/en/news/feature/2025/03/12/breaking-barriers-boosting-women-s-labor-force-participation-in-egypt",
                "Shows active responses and warns against interpreting the residual as absence of reform.",
                "after",
            )
        ],
        "overall_confidence": "medium",
        "limitations": [
            "The residual combines several employment dimensions and does not reveal which component drives Egypt's position.",
            "Most sources are descriptive or programmatic; they do not causally attribute the residual to a specific barrier.",
            "One useful synthesis was published in 2025, after the modeled period, although it discusses long-running constraints.",
        ],
        "sources": ["World Bank", "International Labour Organization"],
        "no_evidence": ["A country-wide causal decomposition of the model residual into childcare, norms, transport and job-structure effects."],
    },
    "CONV-U-008": {
        "mechanisms": [
            {
                "mechanism": "Unpaid household and care work may keep educated women outside paid employment or constrain the type of work they can accept.",
                "supporting_evidence": [
                    evidence(
                        "The report finds that female NEET status outside the labor force is dominated by household reproduction and care work.",
                        "International Labour Organization",
                        "Young persons not in employment and education in India: 2000–2019",
                        2020,
                        "https://www.ilo.org/publications/young-persons-not-employment-and-education-india-2000-2019",
                        "Connects women's non-employment directly to unpaid household production during most of the modeled period.",
                        "during",
                    ),
                    evidence(
                        "The assessment reports that 59 percent of women outside the labor force cite childcare or housework and that recent participation growth is concentrated in self-employment and unpaid work.",
                        "World Bank",
                        "India: Pathways to Prosperity—A Gender Assessment",
                        2025,
                        "https://documents1.worldbank.org/curated/en/099122425090534097/pdf/BOSIB-974f863f-adc1-4b78-934d-d52add12c2b6.pdf",
                        "Supports the care mechanism and clarifies that participation alone may overstate economic opportunity.",
                        "after",
                    ),
                ],
                "confidence": "medium",
                "confidence_reason": "National evidence repeatedly identifies care work, but the sources do not estimate its share of the modeled conversion gap.",
            },
            {
                "mechanism": "The available job mix may not supply enough acceptable, safe and high-quality paid work for increasingly educated women.",
                "supporting_evidence": [
                    evidence(
                        "The report documents a long decline in female labor-force participation through 2019 and a later rebound, while emphasizing large gender gaps and the quality and vulnerability of women's work.",
                        "International Labour Organization",
                        "India Employment Report 2024: Youth employment, education and skills",
                        2024,
                        "https://www.ilo.org/sites/default/files/2024-08/India%20Employment%20-%20web_8%20April.pdf",
                        "Places the signal in the context of job structure, education and uneven job quality rather than education attainment alone.",
                        "during",
                    ),
                    evidence(
                        "The gender assessment notes that education expansion coincided with declining female labor-force participation and discusses norms, childcare and the limited reach of formal-sector protections.",
                        "World Bank",
                        "India Gender Portfolio Review",
                        2017,
                        "https://documents1.worldbank.org/curated/en/377711511422588789/pdf/Main-Report.pdf",
                        "Directly documents the historical education-employment tension underlying the statistical question.",
                        "during",
                    ),
                ],
                "confidence": "medium",
                "confidence_reason": "The structural account is consistent across sources, but India-wide aggregates conceal strong state, rural-urban, caste and class heterogeneity.",
            },
        ],
        "contradicting_or_complicating_evidence": [
            evidence(
                "Female labor-force participation rose substantially after 2019, although much of the increase was in self-employment and unpaid family work.",
                "International Labour Organization",
                "India Employment Report 2024: Youth employment, education and skills",
                2024,
                "https://www.ilo.org/sites/default/files/2024-08/India%20Employment%20-%20web_8%20April.pdf",
                "Challenges a simple story of uninterrupted deterioration and makes employment quality essential to interpretation.",
                "during",
            ),
            evidence(
                "The Gender Data Portal reports recent female labor-force participation near one-third, but also high vulnerable employment and a large remaining gap with men.",
                "World Bank",
                "India — Gender Data Portal",
                2025,
                "https://genderdata.worldbank.org/en/economies/india",
                "Provides a more recent benchmark and shows why indicator definitions and work quality can change the narrative.",
                "after",
            ),
        ],
        "overall_confidence": "medium",
        "limitations": [
            "India's national residual masks major differences by state, caste, religion, income, rurality and age.",
            "Recent participation increases do not necessarily represent gains in paid or secure work.",
            "The evidence supports plausible mechanisms but not causal attribution for the cross-country residual.",
        ],
        "sources": ["International Labour Organization", "World Bank"],
        "no_evidence": ["A harmonized causal estimate linking a specific increase in women's education to paid-employment outcomes across all Indian states."],
    },
    "CONV-P-001": {
        "mechanisms": [
            {
                "mechanism": "Broad female labor-force participation may lift Togo's employment score relative to countries with similar education, finance, digital and macro conditions.",
                "supporting_evidence": [
                    evidence(
                        "The country gender landscape reports near parity in female and male labor-force participation in its latest estimate.",
                        "World Bank",
                        "Togo Gender Data Landscape",
                        2022,
                        "https://documents1.worldbank.org/curated/en/099930107032270670/pdf/IDU023e151a3048ea046610937c02e7924f61b47.pdf",
                        "The near-participation parity is consistent with a positive employment residual relative to peer expectations.",
                        "during",
                    )
                ],
                "confidence": "medium",
                "confidence_reason": "The participation statistic is directly relevant, but it does not establish why Togo differs from modeled peers.",
            },
            {
                "mechanism": "Women's economic activity may be sustained through informal and vulnerable work rather than high-quality formal employment.",
                "supporting_evidence": [
                    evidence(
                        "The same landscape reports substantially higher vulnerable employment among women than men and large gender gaps in account ownership, internet use and land ownership.",
                        "World Bank",
                        "Togo Gender Data Landscape",
                        2022,
                        "https://documents1.worldbank.org/curated/en/099930107032270670/pdf/IDU023e151a3048ea046610937c02e7924f61b47.pdf",
                        "Suggests that a relatively favorable employment residual may coexist with weak job quality and limited economic autonomy.",
                        "during",
                    )
                ],
                "confidence": "medium",
                "confidence_reason": "The descriptive evidence is strong, but the composite score's exact sensitivity to vulnerable employment requires component-level decomposition.",
            },
        ],
        "contradicting_or_complicating_evidence": [
            evidence(
                "Historical legal indicators documented inequalities in property, inheritance and aspects of women's legal capacity despite substantial female labor-force participation.",
                "World Bank",
                "Women, Business and the Law 2010",
                2010,
                "https://wbl.worldbank.org/content/dam/sites/wbl/documents/2021/02/WBL2010.pdf",
                "Shows that participation can coexist with legal constraints and should not be read as full opportunity conversion.",
                "before",
            )
        ],
        "overall_confidence": "low",
        "limitations": [
            "Only a small set of country-specific institutional sources was located for the exact modeled period.",
            "Near participation parity may partly reflect necessity-driven informal work rather than strong returns to education.",
            "The evidence does not identify a policy or institution that causally produced the positive residual.",
        ],
        "sources": ["World Bank"],
        "no_evidence": ["A peer-reviewed or institutional causal evaluation explaining Togo's positive out-of-fold residual.", "A recent country-specific decomposition of education-to-job transitions by job quality."],
    },
    "CONV-P-004": {
        "mechanisms": [
            {
                "mechanism": "High measured female participation may make Mozambique outperform peers on employment access even when job quality is limited.",
                "supporting_evidence": [
                    evidence(
                        "A World Bank project annex reports female and male labor-force participation at 78 and 79 percent in 2021, while also noting continued gender gaps in management and sectoral concentration.",
                        "World Bank",
                        "Mozambique Women Economic Empowerment Project Annex",
                        2022,
                        "https://documents1.worldbank.org/curated/en/099840008042230800/pdf/BOSIB06a21fb800430ac95087a2dee12798.pdf",
                        "The reported participation parity is consistent with the positive residual, while the accompanying caveats constrain its interpretation.",
                        "during",
                    )
                ],
                "confidence": "low",
                "confidence_reason": "Other institutional sources report very different participation levels, indicating definition, year or population inconsistencies.",
            },
            {
                "mechanism": "Informal enterprise and low-productivity work may absorb women without creating strong advancement or earnings pathways.",
                "supporting_evidence": [
                    evidence(
                        "The assessment reports that women entrepreneurs face barriers and are overrepresented in microenterprises, low-growth sectors and the informal economy.",
                        "International Labour Organization",
                        "Enabling Environment for Women in Growth Enterprises in Mozambique",
                        2011,
                        "https://www.ilo.org/publications/enabling-environment-women-growth-enterprises-mozambique",
                        "Provides a plausible reason that employment access can look relatively strong while opportunity quality remains weak.",
                        "during",
                    ),
                    evidence(
                        "The employment diagnostic finds that strong economic performance did not translate into sufficiently improved labor outcomes and emphasizes structural transformation, decent jobs and skills.",
                        "International Labour Organization",
                        "Structural change, employment and education in Mozambique",
                        2015,
                        "https://www.ilo.org/publications/structural-change-employment-and-education-mozambique",
                        "Links education and labor-market outcomes to the economy's limited creation of productive jobs.",
                        "during",
                    ),
                ],
                "confidence": "medium",
                "confidence_reason": "Multiple sources support the job-quality mechanism, but not its causal relation to the model residual.",
            },
        ],
        "contradicting_or_complicating_evidence": [
            evidence(
                "A UN Women–ILO fiscal-policy report gives a much lower female participation estimate than the World Bank annex and documents persistent discrimination, service constraints and pandemic setbacks.",
                "UN Women and International Labour Organization",
                "Fiscal policy and gender equality: Mozambique country report",
                2024,
                "https://www.ilo.org/sites/default/files/2024-07/UNWomen-ILO%20Consolidated%20report_Fiscal_Final_Edited%20Jan%2024.pdf",
                "The conflicting estimate lowers confidence and requires reconciliation of source year, age range and labor-force definitions.",
                "during",
            ),
            evidence(
                "Research on girls' and women's aspirations finds that desired occupations are not always aligned with sectors able to absorb workers and highlights norms, family gatekeeping and financial constraints.",
                "World Bank",
                "A Girl Can Dream: Analyzing Aspirations, Gender Norms, and Influencers among Girls and Women in Mozambique",
                2023,
                "https://www.worldbank.org/en/country/mozambique/publication/a-girl-can-dream-analyzing-aspirations-gender-norms-and-influencers-among-girls-and-women-in-mozambique",
                "Complicates any claim that high participation represents successful conversion into desired or productive work.",
                "during",
            ),
        ],
        "overall_confidence": "low",
        "limitations": [
            "Institutional sources provide conflicting female labor-force participation estimates that likely use different definitions or reference periods.",
            "The positive residual may reflect broad access to low-productivity work rather than strong education-to-career conversion.",
            "No located source causally explains Mozambique's cross-country model residual.",
        ],
        "sources": ["World Bank", "International Labour Organization", "UN Women"],
        "no_evidence": ["A reconciled official time series that explains the large discrepancy in published female participation estimates.", "A causal estimate of which policy generated the positive residual."],
    },
    "CONV-D-003": {
        "mechanisms": [
            {
                "mechanism": "Women's heavy unpaid-care burden and limited childcare may interrupt or constrain employment even as education improves.",
                "supporting_evidence": [
                    evidence(
                        "The project completion report states that women perform about 90 percent of unpaid care, that childbirth is associated with labor-market exit and that childcare access is limited.",
                        "World Bank",
                        "Cambodia Community-Based Childcare for Garment Factory Workers Project — Implementation Completion and Results Report",
                        2024,
                        "https://documents1.worldbank.org/curated/en/099093024201032461/pdf/P1710631889fc6041a6d911a25a5ac4729.pdf",
                        "Directly documents a transition barrier between schooling and sustained employment during the end of the study period.",
                        "during",
                    )
                ],
                "confidence": "medium",
                "confidence_reason": "The care burden is directly documented, but the project evidence does not estimate its contribution to the national divergence score.",
            },
            {
                "mechanism": "A narrow, low-skill and informal job structure may limit the employment-quality returns to educational progress.",
                "supporting_evidence": [
                    evidence(
                        "The employment diagnostic describes high participation and low unemployment alongside pervasive informality, low education, a narrow economic base and skills mismatch.",
                        "International Labour Organization",
                        "Cambodia: Addressing the skills gap — Employment diagnostic study",
                        2015,
                        "https://www.ilo.org/publications/cambodia-addressing-skills-gap-employment-diagnostic-study",
                        "Shows why high participation can coexist with weak conversion into productive, secure work.",
                        "during",
                    ),
                    evidence(
                        "The skills report describes women's concentration in low-skill manufacturing and services, limited advancement, care constraints and gender norms.",
                        "World Bank",
                        "Cambodia Skills for Better Jobs",
                        2023,
                        "https://documents1.worldbank.org/curated/en/099080823003040193/pdf/P1791590b50c330508d11084f55d7a843a.pdf",
                        "Connects improved skills and education to weak job progression and occupational concentration.",
                        "during",
                    ),
                ],
                "confidence": "medium",
                "confidence_reason": "The structural diagnosis is consistent across sources, but the national composite masks sector and cohort differences.",
            },
        ],
        "contradicting_or_complicating_evidence": [
            evidence(
                "Cambodia's garment and footwear sector supported roughly one million jobs, around four-fifths held by women, providing regular employment and income despite a gender pay gap.",
                "International Labour Organization",
                "Cambodia Garment and Footwear Sector Bulletin, Issue 8",
                2019,
                "https://www.ilo.org/publications/cambodia-garment-and-footwear-sector-bulletin-issue-8-december-2018",
                "Shows that Cambodia has generated large-scale employment for women and contradicts a simple claim of absent employment conversion.",
                "during",
            )
        ],
        "overall_confidence": "medium",
        "limitations": [
            "The divergence measure compares composite gender gaps, not a tracked cohort moving from school into work.",
            "High labor-force participation means the shortfall may concern job quality, advancement or vulnerability more than entry into work.",
            "Garment-sector concentration makes national outcomes sensitive to sector-specific shocks and definitions.",
        ],
        "sources": ["World Bank", "International Labour Organization"],
        "no_evidence": ["A national causal decomposition of how much childcare, skills mismatch and garment-sector concentration each contributes to the divergence."],
    },
    "CONV-D-005": {
        "mechanisms": [
            {
                "mechanism": "Education gains may exceed the supply of suitable private-sector jobs, producing queuing for public employment, underemployment or migration.",
                "supporting_evidence": [
                    evidence(
                        "The labor-market assessment describes segmentation by gender, location and education, concentration of women and rural workers in low-productivity agriculture, elevated NEET risk for young women and queuing for public-sector jobs among educated workers.",
                        "World Bank",
                        "A Strong Labor Market Is Key to Bhutan’s Inclusive Growth",
                        2024,
                        "https://www.worldbank.org/en/news/feature/2024/03/11/a-strong-labor-market-is-key-to-bhutan-s-inclusive-growth",
                        "Directly links expanding education to a labor market that may not provide enough suitable productive jobs.",
                        "during",
                    )
                ],
                "confidence": "medium",
                "confidence_reason": "The institutional diagnosis matches the divergence signal but is not a causal estimate of the composite gap.",
            },
            {
                "mechanism": "Childcare, household work and occupational segregation may reduce continuity and quality of women's employment after schooling.",
                "supporting_evidence": [
                    evidence(
                        "The feature reports a persistent participation gap, disproportionate childcare constraints and limited receipt of maternity benefits among new mothers.",
                        "World Bank",
                        "Fostering Childcare to Enable Female Labor Force Participation in Bhutan",
                        2024,
                        "https://blogs.worldbank.org/en/endpovertyinsouthasia/fostering-childcare-to-enable-female-labor-force-participation-i",
                        "Documents a care-related transition barrier at the end of the study period.",
                        "during",
                    ),
                    evidence(
                        "The country gender policy report finds improvement in female participation but persistent job-quality and earnings gaps associated with education endowments, occupational segregation, household chores and childcare.",
                        "World Bank",
                        "Bhutan Gender Policy Note",
                        2013,
                        "https://documents1.worldbank.org/curated/en/960591468017989867/pdf/ACS45510PNT0P10Box0379884B00PUBLIC0.pdf",
                        "Provides longer-run evidence that participation and educational gains did not eliminate employment-quality constraints.",
                        "during",
                    ),
                ],
                "confidence": "medium",
                "confidence_reason": "The channel is supported across periods, but the evidence is descriptive and one source is older.",
            },
        ],
        "contradicting_or_complicating_evidence": [
            evidence(
                "The gender data landscape reports female lower-secondary completion above male completion, while female participation remains below male participation and vulnerable employment remains high for both sexes.",
                "World Bank",
                "Bhutan Gender Data Landscape",
                2022,
                "https://documents1.worldbank.org/curated/en/099502206242210197/pdf/IDU12f89089c170d814a7d1b2ef155431ac8ff82.pdf",
                "Confirms the education-employment tension but also shows that vulnerability is a broader labor-market issue rather than a women-only problem.",
                "during",
            ),
            evidence(
                "An earlier country profile documented rapid movement toward education parity and noted that some young female cohorts had relatively stronger participation than older women.",
                "World Bank",
                "Bhutan Country Gender Profile",
                2016,
                "https://documents1.worldbank.org/curated/en/566161487277272050/pdf/112879-WP-PUBLIC-June-2016-SARRGAPFYUpdatedFYQfinal.pdf",
                "Age-pattern variation cautions against treating the national average as one uniform female trajectory.",
                "during",
            ),
        ],
        "overall_confidence": "medium",
        "limitations": [
            "Bhutan's small population makes national estimates more sensitive to survey design and year-to-year variation.",
            "The divergence score is not a longitudinal transition rate for the same women.",
            "The sources identify several coexisting constraints but do not establish which one causes the measured shortfall.",
        ],
        "sources": ["World Bank"],
        "no_evidence": ["A recent causal study that separates job-supply constraints from childcare and occupational segregation in explaining the national conversion shortfall."],
    },
}


reports = []
for task_id, body in curated.items():
    task = task_by_id[task_id]
    reports.append(
        {
            "task_id": task_id,
            "country": {"iso3": task["iso"], "name": task["country"]},
            "statistical_signal": {
                "statement": task["statistical_signal"],
                "period": task["period"],
                "uncertainty_note": "This is a descriptive, model-dependent signal based on composite indicators and cross-country comparisons; it is not a causal estimate.",
            },
            "mechanisms": body["mechanisms"],
            "contradicting_or_complicating_evidence": body["contradicting_or_complicating_evidence"],
            "overall_confidence": body["overall_confidence"],
            "causal_conclusion": False,
            "limitations": body["limitations"],
            "search_summary": {
                "sources_searched": body["sources"],
                "no_evidence_found_for": body["no_evidence"],
            },
        }
    )


schema = json.loads(SCHEMA.read_text())
validator = Draft202012Validator(schema, format_checker=FormatChecker())
errors = []
for report in reports:
    for error in validator.iter_errors(report):
        errors.append({"task_id": report["task_id"], "path": list(error.path), "message": error.message})

if errors:
    raise SystemExit(json.dumps(errors, indent=2))

REPORTS.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in reports) + "\n")

lines = [
    "# Pilot evidence-agent results",
    "",
    "Research question: **Why does women’s educational progress translate into employment opportunity in some countries but stall in others?**",
    "",
    "These reports contextualize statistical signals; none asserts causality.",
    "",
    "| Country | Trigger | Overall confidence | Main interpretation |",
    "|---|---|---|---|",
]
for report in reports:
    task = task_by_id[report["task_id"]]
    kind = task["kind"].replace("_", " ")
    main = report["mechanisms"][0]["mechanism"]
    lines.append(f"| {report['country']['name']} | {kind} | {report['overall_confidence']} | {main} |")

lines += [
    "",
    "## Cross-case reading",
    "",
    "- **Egypt and India:** evidence most consistently points to unpaid care plus a shortage of acceptable, secure paid jobs. India’s recent participation rebound means the outcome must distinguish paid and secure work from unpaid or vulnerable work.",
    "- **Togo and Mozambique:** their positive residuals should not be labeled success without qualification. Broad participation can coexist with informality, vulnerability, weak financial autonomy and sectoral concentration.",
    "- **Cambodia and Bhutan:** educational progress appears to run ahead of job quality and progression. Cambodia’s garment employment and Bhutan’s education parity are real gains, but care burdens, narrow job structures and occupational concentration remain plausible bottlenecks.",
    "",
    "## What the pilot changed",
    "",
    "The most defensible application should not rank countries on a single ‘conversion success’ score. It should show separate layers for **access to work**, **job quality**, **care constraints**, and **advancement**, with evidence cards and explicit confidence. The contradiction search is essential: it prevented high participation in Togo, Mozambique and Cambodia from being mistaken for unqualified empowerment.",
]
SUMMARY.write_text("\n".join(lines) + "\n")

AUDIT.write_text(
    json.dumps(
        {
            "schema": str(SCHEMA.relative_to(ROOT)),
            "report_file": str(REPORTS.relative_to(ROOT)),
            "report_count": len(reports),
            "task_ids": [r["task_id"] for r in reports],
            "schema_valid": True,
            "validation_errors": [],
            "causal_conclusion_false_count": sum(r["causal_conclusion"] is False for r in reports),
            "reports_with_complicating_evidence": sum(bool(r["contradicting_or_complicating_evidence"]) for r in reports),
            "reports_with_source_urls": sum(
                all(
                    ev["url"].startswith("https://")
                    for mechanism in r["mechanisms"]
                    for ev in mechanism["supporting_evidence"]
                )
                for r in reports
            ),
        },
        indent=2,
    )
    + "\n"
)

print(f"Wrote {len(reports)} validated reports to {REPORTS}")
print(f"Wrote summary to {SUMMARY}")
print(f"Wrote audit to {AUDIT}")
