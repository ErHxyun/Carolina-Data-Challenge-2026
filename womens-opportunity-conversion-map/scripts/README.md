# Reproduction scripts

These scripts are included for provenance and continued development.

## Dependencies

```bash
python -m pip install -r requirements.txt
```

## Scripts

- `build_conversion_evidence_tasks.py` generates evidence-agent prompts from conversion residuals and education–employment divergence candidates.
- `build_pilot_evidence_reports.py` builds and schema-validates the six reviewed pilot reports.
- `build_map_visualization_pack.py` joins model outputs, domain indicators, stochastic results, and evidence metadata into map-ready files.

## Full-workspace requirement

The scripts currently expect the original analysis workspace layout and intermediate outputs under `outputs/`. Large raw and intermediate World Bank files are intentionally excluded from this GitHub package.

To make the pipeline fully standalone, either:

1. place this repository at the root of the full analysis workspace; or
2. update the input paths to a configurable external data directory.

The curated files under `data/` can be used immediately without rerunning the scripts.
