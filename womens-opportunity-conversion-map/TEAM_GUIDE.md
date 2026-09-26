# Team guide

## Suggested ownership

### Data and modeling

- Maintain indicator definitions and observation years.
- Re-run conversion, HMM, and first-passage models.
- Check missingness, outliers, and coverage before updating map files.

### Evidence agent

- Run country investigations from `data/evidence/conversion_evidence_prompts.jsonl`.
- Validate every result against `conversion_evidence_report_schema.json`.
- Require supporting and contradicting evidence.
- Never convert a plausible mechanism into a causal conclusion.

### Frontend and map

- Join geographic geometry using `iso3`.
- Read labels, units, palettes, and caveats from `data/map/layer_catalog.json` rather than hard-coding them.
- Keep missing countries visible and clickable.
- Show coverage and period in tooltips.
- Use `country_detail_cards.json` to populate the first version of the side panel.

### Narrative and presentation

- Lead with the education-to-employment conversion question.
- Separate access to work from job quality.
- Present model outputs as uncertainty-aware signals.
- Use evidence cards to explain what is known, contradicted, and still missing.

## Git workflow

1. Create a short feature branch.
2. Do not overwrite reviewed pilot evidence.
3. Keep generated files and scripts in the same pull request.
4. Record changed definitions or model assumptions in the pull-request description.
5. Check that `iso3` remains unique in the wide map table.
6. Check that every new layer has a catalog entry and caveat.

## Before presenting results

- Confirm the observation period shown in the tooltip.
- Confirm the country has enough domain coverage.
- Check whether a high participation rate is driven by vulnerable or unpaid work.
- Read contradicting evidence, not only the leading mechanism.
- Avoid causal language unless a separate causal design supports it.
