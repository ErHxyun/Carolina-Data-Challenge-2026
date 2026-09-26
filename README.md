# Conversion Evidence Agent

This agent investigates whether authoritative external evidence can plausibly contextualize statistical signals about **why women's educational progress translates into employment opportunity in some countries but stalls in others**.

It doesn't explain residuals. Every report keeps four things separate: what the model found, what sources document, the plausible connection being inferred, and what remains unknown. `causal_conclusion` is always `false`.

See [INSPECTION.md](INSPECTION.md) for the observed input schemas, the available tools, format mismatches, and problems found in the reviewed pilot reports.

## Layout

```
evidence_agent/
  config.toml              trusted domains/tiers, blocked domains, search/source limits, date tolerance, retry, paths
  cea/                     the agent (stdlib + jsonschema; requests/pypdf for inspection; anthropic for live mode)
    tasks.py               Stage A  task parser (new + legacy formats), CSV cross-checks, observation windows
    planner.py             Stage B  falsifiable evidence questions + bounded queries per trigger type
    retrieval.py           Stage C  retrievers: fixture | none | live (Anthropic web_search/web_fetch)
    inspect_source.py      Stage C/D open the real document (HTML/PDF), check title, numbers and terms
    judge.py               Stage D/F eligibility, timing, statistic conflicts, confidence rubric, review flags
    compose.py             Stage G  schema-exact report + reviewer/product sidecar
    validate.py, causal.py Stage H  schema + safety validation, one deterministic repair pass
    pipeline.py            orchestration;  store.py resumable run store;  runlog.py structured JSONL log
    summary.py             human-readable Markdown;  cli.py command line
  fixtures/                offline evidence derived from the six reviewed pilots (+ documented corrections)
  eval/                    evaluate.py and gold_labels.json
  tests/                   57 unittest tests (no pytest needed)
inputs/legacy_201/         unchanged copies of prompts.jsonl, findings.jsonl, agent_tools.py, tool_schemas.json
outputs/evidence_agent_runs/   ALL generated output (reviewed inputs are never written)
```

## Setup

Python 3.11+ is required (the project was run with 3.13.11).

```bash
cd "/Users/isotopeatlarge/Documents/Codex/2026-09-26/referenced-chatgpt-conversation-this-is-an/evidence_agent"
```

```bash
python3 -m pip install -r requirements.txt
```

`jsonschema`, `requests` and `pypdf` were already installed here. `anthropic` is needed only for `--backend live`.

## Commands

Run everything from `evidence_agent/`.

Run the unit tests:

```bash
python3 -m unittest discover -s tests -t tests
```

Rebuild the offline fixture from the reviewed pilots (read-only on the pilots):

```bash
python3 fixtures/build_fixtures.py
```

Parse and plan only. No retrieval happens and no files are written:

```bash
python3 -m cea run --task-id CONV-U-003 --dry-run
```

Run one task, several tasks, the six pilots, or all tasks:

```bash
python3 -m cea run --task-id CONV-U-003 --backend fixture
```

```bash
python3 -m cea run --tasks CONV-U-003,CONV-P-001 --backend fixture
```

```bash
python3 -m cea run --pilots --backend fixture --verify-urls --out ../outputs/evidence_agent_runs/fixture_pilots
```

```bash
python3 -m cea run --all --backend fixture --verify-urls --out ../outputs/evidence_agent_runs/fixture_all
```

Re-running a command resumes. Tasks already `completed` or `abstained` with the same backend are skipped. `--force` re-runs them, and reports are still one per task.

Run the legacy regression sample (a stratified sample of the 201 prompts, fixed seed):

```bash
python3 -m cea run --legacy-sample 20 --backend fixture --out ../outputs/evidence_agent_runs/legacy_fixture
```

Validate only. With no argument this checks the reviewed pilots; `--reports` accepts any JSONL file:

```bash
python3 -m cea validate --write ../outputs/evidence_agent_runs/pilot_reports_validation.json
```

Rebuild `summary.md` from the run records:

```bash
python3 -m cea summary --out ../outputs/evidence_agent_runs/fixture_pilots
```

Evaluate:

```bash
python3 eval/evaluate.py --pilot-run ../outputs/evidence_agent_runs/fixture_pilots --all-run ../outputs/evidence_agent_runs/fixture_all --legacy-run ../outputs/evidence_agent_runs/legacy_fixture --out ../outputs/evidence_agent_runs/evaluation
```

Live retrieval (**not executed here**, since there was no API key). It needs `ANTHROPIC_API_KEY` or an `ant auth login` profile, and makes paid API calls:

```bash
python3 -m cea run --pilots --backend live --verify-urls --out ../outputs/evidence_agent_runs/live_pilots
```

`--backend none` runs the pipeline with no evidence at all, which exercises the abstention path.

## Outputs (per run directory)

| File | Content |
|---|---|
| `reports.jsonl` | one schema-valid report per completed or abstained task (machine-readable) |
| `run_records.jsonl` | append-only source of truth: report, validation issues, repair actions and **sidecar** (review flags, evidence audit with tier, timing basis and inspection results, statistic conflicts, product layers, retrieval log including rejected sources) |
| `failures.jsonl` | structured failure records (validation failures after one repair; crashes) |
| `events.jsonl` | structured log; `stage` ∈ parse, plan, search, retrieval, inspection, extraction, contradiction_search, judge, compose, validation, repair, disposition, run |
| `summary.md` | reviewer view: signal → mechanisms → every URL with timing and inline source-check warnings → contradicting evidence → limitations → gaps → rejected sources → flags |

## How it works

1. **Parse (A).** The parser extracts the observed, expected, residual or divergence numbers, checks the arithmetic, cross-checks against the candidate CSVs, and derives the *actual* observation window from indicator years. It rejects malformed tasks with explicit reasons.
2. **Plan (B).** Trigger-specific falsifiable questions are generated from a 21-category mechanism taxonomy. Positive converters must check job quality; divergence tasks check cohort and definition issues. Queries are bounded by `max_searches_per_task`, and the contradiction side is never starved.
3. **Retrieve (C).** In live mode, Claude uses `web_search_20260209` and `web_fetch_20260209`, with blocked low-quality domains and `pause_turn` resumption. A **provenance guard** drops any URL the tools didn't return, so no fabricated links get through. Only sources opened with web_fetch count as inspected; snippets alone are ineligible.
4. **Inspect/extract (D).** `--verify-urls` opens every cited document. It confirms accessibility, checks that the cited title matches the document, and checks that the claim's numbers and key terms occur in it. Timing is taken from the **period the source describes**, never from its publication year. Publication year is used only as an upper bound, since a 2011 report can't describe 2017–2024.
5. **Contradiction search (E).** A separate set of questions looks for evidence that falsifies or complicates the leading reading: participation rose, success is vulnerable work, reforms came late, averages hide heterogeneity, institutions disagree, education quality, measurement.
6. **Judge (F).** Each mechanism is assessed on authority tier, independence (distinct documents and organizations), temporal alignment, directness, contradiction and statistic conflicts. Conflicting statistics keep **both values**, list the possible reasons (year, age range, population, definition), and lower confidence one level with a floor of low.
7. **Compose (G)** writes the schema-exact report plus the sidecar.
8. **Validate (H)** checks JSON, schema, URLs, trusted domains, ≤3 mechanisms, the contradiction requirement, `causal_conclusion`, causal wording, duplicate or reused sources and year plausibility. It repairs once, deterministically, and otherwise writes a failure record.

### Confidence rubric

Confidence rates the contextual evidence, not causal probability.

| Level | Mechanism rule |
|---|---|
| high | ≥3 documents from ≥2 organizations, ≥2 from tier 1–3, all temporally aligned (≥2 with the period stated in the source), ≥2 directly about women's work, no same-category contradiction, no statistic conflict. Rare by design. |
| medium | ≥2 documents, ≥1 tier 1–3 institutional source, ≥1 temporally aligned, ≥1 direct |
| low | anything eligible but below medium (e.g. one uncorroborated document) |
| insufficient | no eligible source from tiers 1–6 |

Overall confidence is the leading mechanism's level. It drops one level (floor: low) for conflicting statistics. For positive converters it also drops one level (floor: low) when job quality is undocumented or documented as vulnerable or informal.

### Causal-language detection

Error-level hits are unhedged causal wording in agent-written text: *caused, explains the residual, proves, due to, led to, drives, attributable to, the main reason*. Hedged wording ("may explain") and causal claims inside source-derived `claim` fields are warnings that force review. Negated uses ("does not establish causality") and hyphenated adjectives ("necessity-driven") are ignored.

### Mandatory human review

A report is flagged when any of these apply: `official_sources_conflict`, `definition_mismatch`, `low_or_insufficient_confidence`, `only_post_period_sources`, `politically_or_legally_sensitive_claim`, `possible_causal_overstatement`, `positive_converter_job_quality_unverified`, `cited_title_not_found_in_document`, `claim_not_confirmed_in_source`, `source_inaccessible`, `source_reused_not_independent`, `retrieved_evidence_rejected`, `reviewed_claim_corrected_after_source_check`, `annotated_time_match_inconsistent_with_publication_year`, `task_parse_warnings`.

### Product layers (map)

The sidecar's `product_layers` keeps these separate: statistical signal, education, access to work, job quality, unpaid care/time, financial and digital autonomy, advancement and leadership, intersectional disadvantage, contextual evidence, contradictory evidence, and confidence and limitations. There's no single "development score", and positive converters carry an explicit note that access and job quality must not be merged.

## Results (2026-09-26, offline fixture backend + live source inspection)

Full tables are in `outputs/evidence_agent_runs/evaluation/evaluation.md`.

| Metric | 6 pilots | all 35 tasks | legacy sample (20) |
|---|---|---|---|
| schema-valid reports | 100% | 100% | 100% |
| completion (completed or abstained) | 100% | 100% (31 countries) | 100% |
| ≥1 supporting source | 100% | 17.1% (the 29 non-pilot tasks have no fixture evidence) | 0% |
| contradicting evidence / explicit none-found | 100% / 0% | 17.1% / 82.9% | 0% / 100% |
| accessible URLs (really fetched) | 100% of 25 items | same | n/a |
| claim terms or numbers found in the document | 80% | same | n/a |
| authoritative-source rate | 100% (tiers 2–3) | same | n/a |
| duplicate within one list / source reuse across lists | 0% / 8% | same | n/a |
| time_match not "unclear" | 100%, but **only 4% have the period stated in the source**; the rest rely on reviewer annotations or publication-year bounds | same | n/a |
| unsupported causal language | 0% | 0% | 0% |
| abstention | 0% | 82.9% | 100% (correct: no evidence available) |
| mandatory review | 83% | 97% | 100% |

**Agreement with the reviewed pilots** (gold labels fixed before the first run; see `eval/gold_labels.json`):
- Leading mechanism category agrees in 5/6 cases (83%), and mean recall of the pilots' mechanisms is 0.92.
- Overall confidence matches exactly in 5/6 cases (83%), and within one level in 6/6.
- Major-caveat recall is 0.89, or 0.83 excluding caveats emitted from templates. Before a composer fix made after the first evaluation, these were 0.83 and 0.67; the fix adds a limitation whenever complicating evidence documents vulnerable, informal or unpaid work. The pre-fix numbers are in `evaluation_before_job_quality_limitation.json`.

**Discrepancies with the pilots, reported rather than tuned away:**
- **Bhutan leading mechanism.** The agent leads with unpaid care (two documents), while the pilot leads with suitable-job shortage and public-sector queuing (one document in the agent's classification).
- **Cambodia confidence.** The agent rates it low; the pilot rates it medium. Every mechanism rests on a single document once sources are classified, and the pilot's broader "narrow job structure" mechanism is split into skills mismatch and occupational segregation.
- **Mozambique caveat.** The agent doesn't report conflicting participation statistics because source inspection showed the cited report has no Mozambique participation figure (see INSPECTION.md).
- **Bhutan caveat.** The survey-sensitivity caveat isn't produced.
- **Planner coverage.** 2 of 28 fixture items are never retrieved: India Employment Report 2024 as supporting evidence (school-to-work isn't in the under-conversion plan) and Mozambique "Structural change…" (job shortage isn't in the positive-converter plan).

**Pilot problems found**, detailed in INSPECTION.md:
- 3 of 25 unique pilot citations link to a different document than the one named. One India item is rejected as a probable wrong URL.
- The Mozambique conflicting-participation claim is unsupported by its source.
- 2 timing labels contradict publication years.
- 3 pilots reuse a single document as if it were independent evidence.

## What could not be executed

- **Live search retrieval** (`--backend live`). No Anthropic credentials or search API are available in this environment. The backend is implemented and unit-tested with a fake client covering `pause_turn` resumption, the provenance guard, snippet-only rejection and refusal handling. It has **not** made a real API call, and the request shape (server tools `web_search_20260209`/`web_fetch_20260209`, the `thinking`/`effort` parameters, and the server-side refusal-fallback beta) is unverified against the live API. Set `refusal_fallback = false` in `config.toml` if your deployment rejects that beta.
- Consequently, no metric measures retrieval quality. In fixture mode the agent reuses the pilots' own sources, so pilot agreement tests planning, classification and the rubric, not search.
- The supplied `agent_tools.py` can't run because its `ui/` data directory is missing.

## Known limitations

- Category classification uses keyword cues (fixture mode, and the fallback in live mode). It's transparent but brittle.
- Source inspection is heuristic. It can confirm that terms and numbers *occur* in a document, not that a paraphrase is faithful. Dynamic pages and figures inside images can't be checked.
- Caveat agreement is keyword-detected, and two caveats are templated in every report.
- Tier-1 detection of national sources relies on a short domain list plus gov-style host labels.
- The legacy regression checks parsing, scoping, schema validity, causal safety and abstention only, because no completed legacy reports exist.
