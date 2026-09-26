# Women’s Opportunity Conversion Map

An AI-for-Social-Good research project investigating:

> **Why does women’s educational progress translate into employment opportunity in some countries but stall in others?**

The project combines World Bank indicators, statistical anomaly detection, stochastic models, an interactive world-map concept, and an evidence-retrieval agent. Statistical results identify countries worth investigating; the evidence agent retrieves supporting and contradicting institutional evidence without claiming causality.

## Start here

| If you want to… | Open… |
|---|---|
| Understand the research narrative | [`docs/research_design.md`](docs/research_design.md) |
| Add data to the map | [`data/map/layer_catalog.csv`](data/map/layer_catalog.csv) |
| Load one row per country | [`data/map/country_map_layers.csv`](data/map/country_map_layers.csv) |
| Load data in long format | [`data/map/map_layers_long.csv`](data/map/map_layers_long.csv) |
| Build a country detail panel | [`data/map/country_detail_cards.json`](data/map/country_detail_cards.json) |
| Inspect evidence-agent results | [`data/evidence/pilot_evidence_reports.jsonl`](data/evidence/pilot_evidence_reports.jsonl) |
| Understand the evidence-agent contract | [`docs/evidence_agent.md`](docs/evidence_agent.md) |
| See the previous map prototype | [`app/legacy_stage_map.html`](app/legacy_stage_map.html) |

## What is included

```text
womens-opportunity-conversion-map/
├── README.md
├── TEAM_GUIDE.md
├── requirements.txt
├── app/
│   ├── README.md
│   └── legacy_stage_map.html
├── data/
│   ├── map/
│   │   ├── country_map_layers.csv
│   │   ├── map_layers_long.csv
│   │   ├── layer_catalog.csv
│   │   ├── layer_catalog.json
│   │   ├── country_detail_cards.json
│   │   └── pack_audit.json
│   └── evidence/
│       ├── conversion_evidence_prompts.jsonl
│       ├── conversion_evidence_report_schema.json
│       ├── pilot_evidence_reports.jsonl
│       ├── pilot_evidence_summary.md
│       ├── pilot_evidence_validation.json
│       ├── conversion_residual_candidates.csv
│       └── education_employment_divergence_candidates.csv
├── docs/
│   ├── research_design.md
│   ├── map_layers.md
│   └── evidence_agent.md
└── scripts/
    ├── README.md
    ├── build_conversion_evidence_tasks.py
    ├── build_map_visualization_pack.py
    └── build_pilot_evidence_reports.py
```

## Recommended map story

1. **Education ahead of employment** — where are women’s education outcomes furthest ahead of their employment opportunity?
2. **Conversion surprise** — where is employment opportunity better or worse than a cross-validated model expected?
3. **Momentum** — is the modeled gap closing, flat, or widening?
4. **Persistence** — what is the modeled probability that the employment gap will not halve within 15 years?
5. **Possible bottlenecks** — inspect unpaid-care time, finance, digital access, identity, and rural infrastructure separately.
6. **Data visibility** — show missing domains and mismatched observation years.
7. **Evidence** — display supporting evidence, contradicting evidence, confidence, and limitations for reviewed countries.

## Important interpretation rules

- A model residual is an **investigation trigger**, not a causal effect.
- High labor-force participation is not automatically empowerment; it may include informal, vulnerable, or unpaid work.
- “Development delay” describes trajectory resemblance, not that women are literally a fixed number of years behind men.
- Education and employment indicators may describe different cohorts and years.
- Missing data must remain missing; it is not zero and not evidence of poor performance.
- The previous threshold-based stages are retained only as a legacy prototype. New map layers favor continuous measures and explicit uncertainty.

## Current coverage

- 209 country or economy rows.
- 18 available map layers; 16 are recommended for the main interface.
- 176 countries with conversion residuals.
- 170 countries with education–employment divergence diagnostics.
- 186 countries with gap-momentum states.
- 183 countries with first-passage estimates.
- 6 manually reviewed evidence-agent pilot reports.

See [`data/map/pack_audit.json`](data/map/pack_audit.json) for exact machine-readable coverage.

## Local preview

The previous self-contained map prototype can be opened directly in a browser:

```bash
open app/legacy_stage_map.html
```

It does **not yet display all 18 new layers**. The new frontend should join map geometry to `country_map_layers.csv` using the three-letter `iso3` code.

## Reproducibility

The included scripts document how the curated outputs were produced. They expect the fuller analysis workspace and source outputs described in [`scripts/README.md`](scripts/README.md). The GitHub package intentionally contains reviewed, shareable outputs rather than several large raw World Bank archives.

## Status

This is a research prototype. Statistical signals and evidence reports should be reviewed before publication or policy use.
