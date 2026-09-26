# Evidence agent

## Purpose

The evidence agent investigates statistical anomalies using authoritative sources. It does not invent mechanisms or assert causal explanations.

## Trigger groups

- Persistent under-conversion.
- Positive conversion residuals.
- Education progress without employment conversion.

## Required behavior

For each task, the agent must:

1. preserve the original statistical signal and uncertainty;
2. search authoritative institutional or primary sources;
3. identify no more than three plausible mechanisms;
4. perform a separate contradiction search;
5. record organization, title, year, URL, relevance, and time match;
6. assign calibrated confidence;
7. state limitations and missing evidence;
8. return schema-valid JSON;
9. set `causal_conclusion` to `false`.

## Pilot reports

Six manually reviewed pilots are included:

- Egypt;
- India;
- Togo;
- Mozambique;
- Cambodia;
- Bhutan.

The pilots demonstrate why contradiction search matters. High participation in Togo, Mozambique, and Cambodia can coexist with informality, vulnerable work, occupational concentration, or limited advancement.

## File roles

| File | Role |
|---|---|
| `conversion_evidence_prompts.jsonl` | Investigation tasks generated from statistical triggers. |
| `conversion_evidence_report_schema.json` | Required structured output contract. |
| `pilot_evidence_reports.jsonl` | Six reviewed example reports. |
| `pilot_evidence_validation.json` | Schema and safety audit. |
| `pilot_evidence_summary.md` | Human-readable cross-case summary. |

## Language guardrail

Use “is consistent with,” “may contextualize,” or “is a plausible mechanism.” Do not use “caused,” “proved,” or “explains the residual” unless a separate causal study directly establishes that claim.
