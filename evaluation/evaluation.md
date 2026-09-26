# Evidence agent evaluation

Offline evaluation. Live retrieval (web search) could not be executed in this environment; no metric below measures live search quality.

## Pilot Run metrics

| Metric | Value |
|---|---|
| tasks | 6 |
| dispositions | {"completed": 6} |
| completion_rate_pct | 100.0 |
| countries_with_report | 6 |
| schema_valid_rate_pct | 100.0 |
| with_supporting_source_pct | 100.0 |
| with_contradicting_evidence_pct | 100.0 |
| explicit_no_contradiction_found_pct | 0.0 |
| evidence_items | 25 |
| accessible_url_pct | 100.0 |
| claim_terms_or_numbers_confirmed_pct | 80.0 |
| authoritative_source_rate_pct | 100.0 |
| tier_distribution | {"2": 18, "3": 7} |
| duplicate_within_list_rate_pct | 0.0 |
| source_reuse_rate_pct | 8.0 |
| temporal_match_completeness_pct | 100.0 |
| period_stated_in_source_pct | 4.0 |
| time_match_distribution | {"before": 3, "during": 19, "after": 3} |
| unsupported_causal_language_rate_pct | 0.0 |
| possible_causal_overstatement_warning_rate_pct | 0.0 |
| causal_conclusion_false_pct | 100.0 |
| abstention_rate_pct | 0.0 |
| overall_confidence_distribution | {"medium": 3, "low": 3} |
| mandatory_review_rate_pct | 83.3 |
| review_flag_counts | {"annotated_time_match_inconsistent_with_publication_year": 2, "cited_title_not_found_in_document": 2, "fixture_evidence_not_live_retrieved": 6, "source_reused_not_independent": 2, "retrieved_evidence_rejected": 1, "low_or_insufficient_confidence": 3, "politically_or_legally_sensitive_claim": 1, "reviewed_claim_corrected_after_source_check": 1} |

## All Tasks Run metrics

| Metric | Value |
|---|---|
| tasks | 35 |
| dispositions | {"abstained": 29, "completed": 6} |
| completion_rate_pct | 100.0 |
| countries_with_report | 31 |
| schema_valid_rate_pct | 100.0 |
| with_supporting_source_pct | 17.1 |
| with_contradicting_evidence_pct | 17.1 |
| explicit_no_contradiction_found_pct | 82.9 |
| evidence_items | 25 |
| accessible_url_pct | 100.0 |
| claim_terms_or_numbers_confirmed_pct | 80.0 |
| authoritative_source_rate_pct | 100.0 |
| tier_distribution | {"2": 18, "3": 7} |
| duplicate_within_list_rate_pct | 0.0 |
| source_reuse_rate_pct | 8.0 |
| temporal_match_completeness_pct | 100.0 |
| period_stated_in_source_pct | 4.0 |
| time_match_distribution | {"before": 3, "during": 19, "after": 3} |
| unsupported_causal_language_rate_pct | 0.0 |
| possible_causal_overstatement_warning_rate_pct | 0.0 |
| causal_conclusion_false_pct | 100.0 |
| abstention_rate_pct | 82.9 |
| overall_confidence_distribution | {"insufficient": 29, "medium": 3, "low": 3} |
| mandatory_review_rate_pct | 97.1 |
| review_flag_counts | {"fixture_evidence_not_live_retrieved": 35, "low_or_insufficient_confidence": 32, "annotated_time_match_inconsistent_with_publication_year": 2, "cited_title_not_found_in_document": 2, "source_reused_not_independent": 2, "retrieved_evidence_rejected": 1, "politically_or_legally_sensitive_claim": 1, "positive_converter_job_quality_unverified": 8, "reviewed_claim_corrected_after_source_check": 1} |

## Legacy Run metrics

| Metric | Value |
|---|---|
| tasks | 20 |
| dispositions | {"abstained": 20} |
| completion_rate_pct | 100.0 |
| countries_with_report | 18 |
| schema_valid_rate_pct | 100.0 |
| with_supporting_source_pct | 0.0 |
| with_contradicting_evidence_pct | 0.0 |
| explicit_no_contradiction_found_pct | 100.0 |
| evidence_items | 0 |
| accessible_url_pct | not measured (run without --verify-urls) |
| claim_terms_or_numbers_confirmed_pct | not measured |
| authoritative_source_rate_pct | None |
| tier_distribution | {} |
| duplicate_within_list_rate_pct | None |
| source_reuse_rate_pct | None |
| temporal_match_completeness_pct | None |
| period_stated_in_source_pct | None |
| time_match_distribution | {} |
| unsupported_causal_language_rate_pct | 0.0 |
| possible_causal_overstatement_warning_rate_pct | 0.0 |
| causal_conclusion_false_pct | 100.0 |
| abstention_rate_pct | 100.0 |
| overall_confidence_distribution | {"insufficient": 20} |
| mandatory_review_rate_pct | 100.0 |
| review_flag_counts | {"fixture_evidence_not_live_retrieved": 20, "legacy_out_of_scope": 18, "low_or_insufficient_confidence": 20} |

## Agreement with reviewed pilots

Fixture mode reuses the pilots' own sources, so this measures whether planning, classification and the rubric reproduce reviewer judgments from the same evidence - not retrieval quality. Caveats are keyword-detected; 'no_causal_attribution' and 'heterogeneity' are emitted from templates in every report, so recall excluding them is the more informative number.

| Task | Country | Agent leading | Gold leading | Match | Agent conf. | Gold conf. | Caveats missing |
|---|---|---|---|---|---|---|---|
| CONV-U-003 | Egypt | unpaid_care | unpaid_care | yes | medium | medium | - |
| CONV-U-008 | India | unpaid_care | unpaid_care | yes | medium | medium | - |
| CONV-P-001 | Togo | broad_participation | broad_participation | yes | low | low | - |
| CONV-P-004 | Mozambique | broad_participation | broad_participation | yes | low | low | conflicting_statistics |
| CONV-D-003 | Cambodia | unpaid_care | unpaid_care | yes | low | medium | - |
| CONV-D-005 | Bhutan | unpaid_care | job_shortage/public_sector_queue | no | medium | medium | measurement |

- leading_mechanism_agreement_pct: 83.3
- mean_gold_mechanism_recall: 0.92
- confidence_exact_agreement_pct: 83.3
- confidence_within_one_level_pct: 100.0
- mean_caveat_recall: 0.89
- mean_caveat_recall_excluding_templated: 0.83

## Planner coverage of fixture evidence

Fixture recall: 92.9%

- CONV-P-004 never retrieved CONV-P-004#03: Structural change, employment and education in Mozambique
- CONV-U-008 never retrieved CONV-U-008#03: India Employment Report 2024: Youth employment, education and skills

## Validator applied to the reviewed pilots (read-only)

- CONV-U-003: errors none; warnings ['source_reused_as_contradiction']
- CONV-U-008: errors none; warnings ['source_reused_as_contradiction']
- CONV-P-001: errors none; warnings ['source_reused_across_mechanisms']
- CONV-P-004: errors none; warnings none
- CONV-D-003: errors none; warnings none
- CONV-D-005: errors none; warnings none

## Legacy regression

- legacy_prompts: 201
- parsed: 201
- rejected: []
- sample_size: 20
- sample_dimensions: {'Infrastructure': 6, 'Health': 10, 'Overall': 2, 'Education': 1, 'Employment': 1}
- flagged_out_of_scope_pct: 90.0
- abstained_pct: 100.0
- note: No completed reports exist for the legacy 201 prompts (only prompts and statistical findings), so regression checks parsing, scoping, schema validity, causal safety and correct abstention when no evidence is available - not agreement with prior answers.

