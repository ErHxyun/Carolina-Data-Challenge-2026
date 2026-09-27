// Data and helper checks for the conversion view. Uses Node's built-in test runner (no new
// dependency):  npm run test:data
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  conversionMapData, defaultYear, formatValue, layerYears, momentum, observationYear, valueFor,
} from '../src/data/conversionScale.js';

const root = new URL('..', import.meta.url);
const read = (path) => JSON.parse(readFileSync(new URL(path, root), 'utf8'));
const dir = 'public/data/conversion/';
const snapshot = read(`${dir}snapshot_atlas.json`).countries;
const timeline = read(`${dir}timeline_atlas.json`).layers;
const { layers } = read(`${dir}layers.json`);
const evidence = read(`${dir}evidence_reports.json`);
const provenance = read(`${dir}provenance.json`);
const codes = read('src/data/researchCountryCodes.json');
const geo = read('src/data/countries.geo.json');
const data = { countries: snapshot, timeline, layerById: Object.fromEntries(layers.map((l) => [l.id, l])) };
const byId = data.layerById;
const isNumOrNull = (v) => v === null || (typeof v === 'number' && Number.isFinite(v));
const geometry = { features: geo.features.filter((f) => f.properties.ADMIN !== 'Antarctica').map((f) => ({ properties: { name: f.properties.ADMIN } })) };
const isoFor = (name) => codes[name] ?? null;

test('1. ISO3 keys are unique, well-formed economies', () => {
  const keys = Object.keys(snapshot);
  assert.equal(new Set(keys).size, keys.length);
  for (const k of keys) assert.match(k, /^[A-Z]{3}$/);
  for (const [id, t] of Object.entries(timeline)) for (const iso of Object.keys(t.values)) assert.match(iso, /^[A-Z]{3}$/, `${id} ${iso}`);
  for (const agg of ['WLD', 'AFE', 'EAP', 'HIC', 'SAS', 'MNA']) {
    assert.ok(!(agg in snapshot), `aggregate ${agg} in snapshot`);
    for (const t of Object.values(timeline)) assert.ok(!(agg in t.values), `aggregate ${agg} in timeline`);
  }
});

test('2 & 8. layer registry is complete and consistent', () => {
  const required = ['id', 'label', 'question', 'type', 'unit', 'palette', 'direction', 'source', 'recommended', 'caveat',
    'display_label', 'short_caveat', 'group', 'temporal', 'value_type', 'scale', 'coverage'];
  assert.equal(new Set(layers.map((l) => l.id)).size, layers.length);
  for (const l of layers) {
    for (const key of required) assert.ok(key in l, `${l.id} missing ${key}`);
    assert.ok(['primary', 'historical', 'more'].includes(l.group), l.id);
    assert.ok(['snapshot', 'timeline', 'waves'].includes(l.temporal), l.id);
    assert.ok(['diverging', 'sequential', 'categorical', 'stepped', 'log'].includes(l.scale.kind), l.id);
    if (l.temporal === 'snapshot') assert.ok(Object.values(snapshot).some((c) => l.id in c), `${l.id} not in snapshot`);
    else assert.ok(timeline[l.id], `${l.id} has no timeline`);
    if (l.temporal === 'waves') assert.deepEqual(l.years, timeline[l.id].years);
    if (l.scale.kind === 'diverging') assert.equal(l.scale.domain[1], 0, `${l.id} not centred on zero`);
  }
  assert.deepEqual(layers.filter((l) => l.group === 'primary').map((l) => l.id), [
    'education_employment_conversion_gap_z', 'conversion_residual', 'conversion_shortfall', 'gap_momentum_state',
    'prob_gap_not_halved_within_15y', 'core_domains_observed']);
  assert.ok(!layers.some((l) => l.id === 'development_delay_employment_years'), 'optional delay layer must not be exposed');
});

test('3. values are numbers or null; timeline arrays align with years', () => {
  for (const l of layers.filter((x) => x.temporal === 'snapshot' && x.scale.kind !== 'categorical')) {
    for (const [iso, c] of Object.entries(snapshot)) assert.ok(isNumOrNull(c[l.id] ?? null), `${iso}.${l.id}=${c[l.id]}`);
  }
  for (const [id, t] of Object.entries(timeline)) {
    for (const [iso, values] of Object.entries(t.values)) {
      assert.equal(values.length, t.years.length, `${id} ${iso}`);
      for (const v of values) assert.ok(isNumOrNull(v), `${id} ${iso} ${v}`);
    }
  }
});

test('4. probabilities lie in [0, 1] and momentum probabilities sum to 1', () => {
  const probs = ['prob_gap_closing', 'prob_gap_flat', 'prob_gap_widening', 'prob_gap_not_halved_within_15y',
    'prob_employment_gap_halves_within_10y', 'prob_rural_time_tax_gap_shrinking', 'observed_missing_share'];
  for (const c of Object.values(snapshot)) {
    for (const p of probs) if (c[p] !== null && c[p] !== undefined) assert.ok(c[p] >= 0 && c[p] <= 1, `${p}=${c[p]}`);
    if (c.gap_momentum_state) assert.ok(Math.abs(c.prob_gap_closing + c.prob_gap_flat + c.prob_gap_widening - 1) < 1e-3);
  }
});

test('5. missing values stay null and are never mapped as zero', () => {
  for (const l of layers.filter((x) => x.temporal === 'snapshot')) {
    const nonNull = Object.values(snapshot).filter((c) => c[l.id] !== null && c[l.id] !== undefined).length;
    assert.equal(nonNull, l.coverage, `${l.id}: coverage metadata disagrees with data`);
  }
  assert.equal(snapshot.BTN.identity_female_pct, null, 'Bhutan has no ID survey wave');
  const layer = byId.time_tax_extra_hours_day;
  const mapped = conversionMapData(geometry, data, layer, isoFor, null);
  const without = mapped.features.filter((f) => !f.properties.hasData);
  assert.ok(without.length > 150, 'time-use data are sparse');
  for (const f of without) {
    assert.ok(!('value' in f.properties), `${f.properties.name} got a value`);
    assert.ok(!('elevation' in f.properties), `${f.properties.name} got an extrusion height`);
  }
  assert.equal(formatValue(layer, null), 'No estimate available');
});

test('6. countries without conversion data stay on the map (clickable) as missing', () => {
  const mapped = conversionMapData(geometry, data, byId.conversion_residual, isoFor, null);
  assert.equal(mapped.features.length, geometry.features.length);
  const greenland = mapped.features.find((f) => f.properties.name === 'Greenland');
  assert.equal(greenland.properties.hasData, false);
  assert.equal(snapshot.GRL, undefined);
});

test('7. evidence reports are keyed by the correct ISO3', () => {
  const keys = Object.keys(evidence.reports).sort();
  assert.deepEqual(keys, ['BTN', 'EGY', 'IND', 'KHM', 'MOZ', 'TGO']);
  for (const [iso, r] of Object.entries(evidence.reports)) {
    assert.equal(r.country.iso3, iso);
    assert.equal(r.causal_conclusion, false);
    assert.ok(r.mechanisms.length <= 3);
    assert.equal(snapshot[iso].evidence_report_available, true);
  }
  const flagged = Object.entries(snapshot).filter(([, c]) => c.evidence_report_available).map(([k]) => k).sort();
  assert.deepEqual(flagged, keys);
  assert.equal(evidence.label, 'Contextual evidence — not causal attribution');
});

test('no interpolation: years stay real, combined values use same-year pairs only', () => {
  const edu = timeline.education_gap_timeline, emp = timeline.employment_gap_timeline, conv = timeline.conversion_gap_timeline;
  for (const [iso, values] of Object.entries(conv.values)) {
    values.forEach((v, i) => {
      if (v === null) return;
      const year = conv.years[i];
      const e = edu.values[iso]?.[edu.years.indexOf(year)], m = emp.values[iso]?.[emp.years.indexOf(year)];
      assert.ok(e !== null && e !== undefined && m !== null && m !== undefined, `${iso} ${year} combined without both inputs`);
    });
  }
  const gaps = Object.values(edu.values).flat().filter((v) => v === null).length;
  assert.ok(gaps > 1000, 'observed education series should contain real gaps, not filled values');
  assert.equal(edu.years.at(-1), 2022, 'education parity ends at its last real observation year');
  assert.deepEqual(timeline.finance_gender_gap_pp.years, [2011, 2014, 2017, 2021, 2022, 2024]);
  assert.ok(Math.max(...Object.values(timeline).map((t) => t.years.at(-1))) <= 2024);
});

test('time handling helpers', () => {
  const finance = byId.finance_gender_gap_pp;
  assert.deepEqual(layerYears(data, byId.conversion_residual), []);
  assert.equal(defaultYear(data, finance), 'latest');
  assert.equal(defaultYear(data, byId.female_lfpr_timeline), 2024);
  const conv = byId.conversion_gap_timeline, y = defaultYear(data, conv);
  assert.ok(y < 2022 && conv.coverage_by_year[y] >= Math.max(...Object.values(conv.coverage_by_year)) / 2, `default ${y} should be well covered`);
  assert.equal(observationYear(data, finance, 'BTN', 'latest'), 2014, 'Bhutan finance gap is a 2014 observation');
  assert.equal(valueFor(data, finance, 'BTN', 2024), null, 'no carry-forward into later waves');
  assert.ok(typeof valueFor(data, finance, 'BTN', 2014) === 'number');
});

test('momentum text always carries all three probabilities', () => {
  const m = momentum(snapshot.EGY);
  assert.match(m.text, /Closing \d+% · Flat \d+% · Widening/);
  assert.equal(m.mismatch, true, 'Egypt label differs from its highest-probability state');
});

test('11. production base path and runtime data URLs', async () => {
  const config = (await import('../vite.config.js')).default({ command: 'build' });
  assert.equal(config.base, '/Carolina-Data-Challenge-2026/');
  const src = fileURLToPath(new URL('src/', root));
  const files = readdirSync(src, { recursive: true }).filter((f) => /\.(js|jsx)$/.test(f));
  for (const f of files) {
    const text = readFileSync(`${src}${f}`, 'utf8');
    for (const match of text.matchAll(/fetch\(([^)]*)\)/g)) {
      assert.ok(!/['"`]\/data\//.test(match[1]), `${f} fetches an absolute /data path`);
    }
    const code = text.split('\n').filter((line) => !/^\s*(\/\/|\*|\/\*)/.test(line)).join('\n');
    for (const line of code.split('\n').filter((l) => l.includes('data/conversion/'))) {
      assert.ok(line.includes('import.meta.env.BASE_URL') || /const base = `\$\{import\.meta\.env\.BASE_URL\}/.test(line), `${f} must build data URLs from BASE_URL: ${line.trim()}`);
    }
  }
  assert.equal(provenance.validation.status, 'passed');
});

test('every map layer explains a single value in plain language, number shown once', async () => {
  const { explainValue, shortValue, hasExplanation } = await import('../src/data/layerExplain.js');
  for (const l of layers) assert.ok(hasExplanation(l.id), `${l.id} has no plain-language caption`);
  assert.deepEqual(explainValue('identity_female_pct', 93.6), { headline: '93.6%', caption: 'of women aged 15+ have an official ID' });
  assert.deepEqual(explainValue('finance_gender_gap_pp', -24.65), { headline: '24.6 pp', caption: 'fewer women than men have a bank or mobile-money account' });
  assert.equal(shortValue('identity_female_pct', 94.9), '94.9%');
  assert.equal(shortValue('finance_gender_gap_pp', -5.2), '5.2 pp fewer women');
  assert.equal(explainValue('identity_female_pct', null), null);
  for (const l of layers) {
    const e = explainValue(l.id, l.scale.kind === 'categorical' ? 'Flat' : 0.3);
    assert.ok(e, l.id);
    assert.ok(!/\d/.test(e.caption.replace(/100,000|15\+|15 years|10 years|1990|35/g, '')), `${l.id} caption repeats a number: ${e.caption}`);
    assert.ok(!/\b(caus|because|due to|explains)\b/i.test(e.caption), `causal wording: ${e.caption}`);
  }
});
