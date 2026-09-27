// Plain-language reading of one country's value, split into a headline number (shown once, with
// its unit) and a caption that continues it: "93.6%" + "of women aged 15+ have an official ID".
// Direction is said in words ("fewer women than men"), so no minus signs are needed.
// Wording is descriptive, never causal. Pure module so `node --test` can check it.

const n1 = (v) => Math.abs(v).toFixed(1);
const n2 = (v) => Math.abs(v).toFixed(2);
const pct = (p) => (p > 0 && p < 0.005 ? '<1%' : p < 1 && p > 0.995 ? '>99%' : `${Math.round(p * 100)}%`);
const near = (v, eps) => Math.abs(v) < eps;

// For each layer: `num` = headline (magnitude + unit), `caption` = what it means for this value,
// `word` = short direction used after the median ("fewer", "below", …; empty when unsigned).
const SPEC = {
  education_gap_timeline: {
    num: (v) => `${n1(v * 100)}%`,
    caption: (v) => (near(v, 0.005) ? 'difference: girls and boys enrol in secondary school at about the same rate' : `${v < 0 ? 'lower' : 'higher'} secondary enrollment for girls than for boys`),
    word: (v) => (v < 0 ? 'lower for girls' : 'higher for girls'),
  },
  employment_gap_timeline: {
    num: (v) => `${n1(v * 100)}%`,
    caption: (v) => (near(v, 0.005) ? 'difference: women and men take part in the labour force at about the same rate' : `${v < 0 ? 'lower' : 'higher'} labour-force participation for women than for men`),
    word: (v) => (v < 0 ? 'lower for women' : 'higher for women'),
  },
  conversion_gap_timeline: {
    num: (v) => `${n2(v)} pts`,
    caption: (v) => (v >= 0 ? 'closer to gender parity in education than in employment' : 'closer to gender parity in employment than in education'),
    word: (v) => (v >= 0 ? 'education closer' : 'employment closer'),
  },
  female_lfpr_timeline: { num: (v) => `${n1(v)}%`, caption: () => 'of women aged 15+ are working or looking for work' },
  female_vulnerable_employment_timeline: { num: (v) => `${n1(v)}%`, caption: () => 'of employed women work on their own account or unpaid in a family business' },
  rural_electricity_gap_timeline: {
    num: (v) => `${n1(v)} pp`,
    caption: (v) => (v >= 0 ? 'lower electricity access in rural than in urban areas' : 'higher electricity access in rural than in urban areas'),
    word: (v) => (v >= 0 ? 'rural lower' : 'rural higher'),
  },
  rural_clean_cooking_gap_timeline: {
    num: (v) => `${n1(v)} pp`,
    caption: (v) => (v >= 0 ? 'lower clean-cooking access in rural than in urban areas' : 'higher clean-cooking access in rural than in urban areas'),
    word: (v) => (v >= 0 ? 'rural lower' : 'rural higher'),
  },
  education_employment_conversion_gap_z: {
    num: (v) => `${n2(v)} SD`,
    caption: (v) => (v >= 0 ? 'more gender-equal in education than in employment' : 'more gender-equal in employment than in education'),
    word: (v) => (v >= 0 ? 'education ahead' : 'employment ahead'),
  },
  conversion_residual: {
    num: (v) => `${n2(v)} SD`,
    caption: (v) => (v < 0 ? "below the women's employment the model expects for similar countries" : "above the women's employment the model expects (not a measure of job quality)"),
    word: (v) => (v < 0 ? 'below expected' : 'above expected'),
  },
  conversion_shortfall: {
    num: (v) => `${n2(v)} SD`,
    caption: (v) => (v >= 0 ? 'more narrowing of education gaps than of employment gaps' : 'more narrowing of employment gaps than of education gaps'),
    word: (v) => (v >= 0 ? 'education faster' : 'employment faster'),
  },
  gap_momentum_state: { num: (v) => String(v), caption: () => "the model's labelled direction for the gender gap" },
  prob_gap_widening: { num: pct, caption: () => 'model chance that the gender gap is currently widening' },
  prob_gap_not_halved_within_15y: { num: pct, caption: () => 'model chance the employment gap is not halved within 15 years' },
  prob_employment_gap_halves_within_10y: { num: pct, caption: () => 'model chance the employment gap halves within 10 years' },
  finance_gender_gap_pp: {
    num: (v) => `${n1(v)} pp`,
    caption: (v) => (v < 0 ? 'fewer women than men have a bank or mobile-money account' : 'more women than men have a bank or mobile-money account'),
    word: (v) => (v < 0 ? 'fewer women' : 'more women'),
  },
  digital_gender_gap_pp: {
    num: (v) => `${n1(v)} pp`,
    caption: (v) => (v < 0 ? 'fewer women than men have digital access' : 'more women than men have digital access'),
    word: (v) => (v < 0 ? 'fewer women' : 'more women'),
  },
  identity_female_pct: { num: (v) => `${n1(v)}%`, caption: () => 'of women aged 15+ have an official ID' },
  time_tax_extra_hours_day: { num: (v) => `${n1(v)} h`, caption: () => 'more per day than men on unpaid care and housework' },
  maternal_mortality_ratio: { num: (v) => `${Math.round(v)}`, caption: () => 'maternal deaths per 100,000 live births' },
  rural_time_tax_gap_latest_pp: {
    num: (v) => `${n1(v)} pts`,
    caption: (v) => (v >= 0 ? 'rural households behind urban ones on time-saving services' : 'rural households ahead of urban ones on time-saving services'),
    word: (v) => (v >= 0 ? 'rural behind' : 'rural ahead'),
  },
  core_domains_observed: { num: (v) => `${v} of 4`, caption: () => 'core areas have comparable data (education, employment, finance, digital)' },
  core_year_spread: { num: (v) => `${Math.round(v)} yrs`, caption: () => 'between the latest figures for different areas' },
  observed_education_years: { num: (v) => `${v} of 35`, caption: () => "years since 1990 in which girls' and boys' enrollment was measured" },
  observed_missing_share: { num: pct, caption: () => 'of possible yearly records in gender statistics are missing' },
};

const missing = (v) => v === null || v === undefined || (typeof v === 'number' && !Number.isFinite(v));

/** { headline, caption } for one value, or null when there is no value or no wording for the layer. */
export function explainValue(layerId, value) {
  const spec = SPEC[layerId];
  if (!spec || missing(value)) return null;
  return { headline: spec.num(value), caption: spec.caption(value) };
}

/** Compact form for comparisons such as the median: "94.9%", "5.2 pp fewer women". */
export function shortValue(layerId, value) {
  const spec = SPEC[layerId];
  if (!spec || missing(value)) return null;
  return spec.word ? `${spec.num(value)} ${spec.word(value)}` : spec.num(value);
}

/** Full sentence form, used where the number is not shown separately (screen readers, tests). */
export function sentence(layerId, value) {
  const e = explainValue(layerId, value);
  return e ? `${e.headline} ${e.caption}.` : null;
}

export const hasExplanation = (layerId) => layerId in SPEC;
