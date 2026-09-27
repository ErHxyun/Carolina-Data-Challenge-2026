// Pure helpers for the education-to-employment conversion layers: colour scales, per-year values,
// formatting and interpretation. No JSON imports, so `node --test` can exercise them directly.
// Layer metadata (labels, units, caveats, scale domains, temporal type) comes from
// public/data/conversion/layers.json.

export const MISSING_COLOR = '#555b65'; // same neutral as the rural–urban map
const NEUTRAL = '#e4e7e9';
const LIGHT = '#f1ece4';

const RAMPS = {
  orange_to_blue_diverging: ['#c2562d', '#f0a36b', NEUTRAL, '#7fc4d6', '#2f7fa0'],
  blue_to_orange_diverging: ['#2f7fa0', '#7fc4d6', NEUTRAL, '#f0a36b', '#c2562d'],
  gold_to_pink_diverging: ['#b8911f', '#e3cc80', NEUTRAL, '#eaa0c3', '#c2477f'],
  light_to_pink_sequential: [LIGHT, '#eaa0c3', '#c2477f', '#7a1f4f'],
  light_to_orange_sequential: [LIGHT, '#ffc278', '#ec7841', '#ad382f'],
  light_to_blue_sequential: [LIGHT, '#9cdee8', '#359db7', '#1d5f7a'],
  light_to_gold_sequential: [LIGHT, '#f3d98b', '#d9a92e', '#8a6a12'],
};
export const STATE_COLORS = { Closing: '#359db7', Flat: '#d8cfbf', Widening: '#ec7841' };
const BOOLEAN_COLORS = { true: '#359db7', false: '#8a8f98' };
const DISPLAY_HEIGHT_M = 120000;

export const VALUE_TYPE_LABEL = {
  observed: 'Observed statistics',
  modelled: 'Modelled estimates',
  mixed: 'Observed education vs modelled employment',
  model_output: 'Research model output',
  compiled: 'Compiled survey and estimate series',
  coverage: 'Coverage metric',
};

export const finiteNumber = (v) => typeof v === 'number' && Number.isFinite(v);

export function rampFor(layer) {
  return RAMPS[layer.palette] ?? (layer.scale.kind === 'diverging' ? RAMPS.orange_to_blue_diverging : RAMPS.light_to_blue_sequential);
}

/** Evenly spaced [value, color] stops for a layer's legend and paint expression. */
export function scaleStops(layer) {
  const { kind, domain } = layer.scale;
  const colors = rampFor(layer);
  if (kind === 'diverging') {
    const d = domain[2];
    return [[-d, colors[0]], [-d / 2, colors[1]], [0, colors[2]], [d / 2, colors[3]], [d, colors[4]]];
  }
  if (kind === 'log') {
    const [lo, hi] = domain.map(Math.log10);
    return colors.map((c, i) => [10 ** (lo + ((hi - lo) * i) / (colors.length - 1)), c]);
  }
  if (kind === 'stepped') {
    const [lo, hi] = domain;
    return Array.from({ length: hi - lo + 1 }, (_, i) => [lo + i, colors[Math.min(colors.length - 1, i)]]);
  }
  const [lo, hi] = domain;
  return colors.map((c, i) => [lo + ((hi - lo) * i) / (colors.length - 1), c]);
}

/** MapLibre paint expression. Countries without data always get the neutral missing colour. */
export function colorExpression(layer) {
  const { kind } = layer.scale;
  let fill;
  if (kind === 'categorical') {
    const colors = layer.type === 'boolean' ? BOOLEAN_COLORS : STATE_COLORS;
    fill = ['match', ['to-string', ['get', 'category']], ...Object.entries(colors).flat(), MISSING_COLOR];
  } else if (kind === 'stepped') {
    const stops = scaleStops(layer);
    fill = ['step', ['get', 'value'], stops[0][1], ...stops.slice(1).flat()];
  } else if (kind === 'log') {
    const stops = scaleStops(layer);
    fill = ['interpolate', ['linear'], ['ln', ['max', ['get', 'value'], stops[0][0]]], ...stops.flatMap(([v, c]) => [Math.log(v), c])];
  } else {
    fill = ['interpolate', ['linear'], ['get', 'value'], ...scaleStops(layer).flat()];
  }
  return ['case', ['!', ['get', 'hasData']], MISSING_COLOR, fill];
}

/** Share of the legend range, used only for the optional display-scale extrusion. */
function magnitude(layer, v) {
  const { kind, domain } = layer.scale;
  if (kind === 'diverging') return Math.min(1.5, Math.abs(v) / domain[2]);
  if (kind === 'log') return Math.max(0, Math.log(Math.max(v, domain[0]) / domain[0]) / Math.log(domain[1] / domain[0]));
  const [lo, hi] = domain;
  return Math.min(1.5, Math.max(0, (v - lo) / (hi - lo || 1)));
}

export const supportsExtrusion = (layer) => layer.scale.kind !== 'categorical';

// ------------------------------------------------------------------ time handling
/** Years a layer can be viewed at: every year in range (timeline), genuine survey waves, or none. */
export function layerYears(data, layer) {
  if (layer.temporal === 'snapshot') return [];
  return data?.timeline?.[layer.id]?.years ?? [];
}

/**
 * Default year when a layer is selected. Timeline: the latest year whose coverage is at least half
 * of the best-covered year (reporting lags leave the final years nearly empty; the slider still
 * reaches them). Waves: the latest-available view.
 */
export function defaultYear(data, layer) {
  if (layer.temporal === 'timeline') {
    const years = layerYears(data, layer);
    const counts = layer.coverage_by_year ?? {};
    const best = Math.max(0, ...Object.values(counts));
    return [...years].reverse().find((y) => (counts[y] ?? 0) >= best / 2) ?? years.at(-1) ?? null;
  }
  if (layer.temporal === 'waves') return 'latest';
  return null;
}

export function seriesFor(timeline, layerId, iso) {
  const entry = timeline?.[layerId];
  const values = iso ? entry?.values[iso] : null;
  return values ? { years: entry.years, values } : null;
}

/** Value for one country. Never carries values across years: a missing year is null. */
export function valueFor(data, layer, iso, year) {
  if (!iso) return null;
  const fromTimeline = layer.temporal === 'timeline' || (layer.temporal === 'waves' && year !== 'latest');
  if (fromTimeline) {
    const series = seriesFor(data?.timeline, layer.id, iso);
    const i = series ? series.years.indexOf(year) : -1;
    return i >= 0 ? series.values[i] ?? null : null;
  }
  return data?.countries?.[iso]?.[layer.id] ?? null;
}

/** The observation year behind a displayed value, when the data record it. */
export function observationYear(data, layer, iso, year) {
  if (layer.temporal === 'timeline' || (layer.temporal === 'waves' && year !== 'latest')) return year;
  return layer.year_field ? data?.countries?.[iso]?.[layer.year_field] ?? null : null;
}

/**
 * Attach one conversion layer (at one year where relevant) to every map feature. Missing values
 * stay missing: `value` and `category` are omitted (never 0), `hasData` is false and no extrusion
 * height is produced.
 */
export function conversionMapData(geometry, data, layer, isoFor, year) {
  return {
    type: 'FeatureCollection',
    features: geometry.features.map((feature) => {
      const iso = isoFor(feature.properties.name);
      const raw = valueFor(data, layer, iso, year);
      const categorical = layer.scale.kind === 'categorical';
      const hasData = categorical ? raw !== null && raw !== undefined : finiteNumber(raw);
      const properties = { ...feature.properties, iso: iso ?? '', layer: layer.id, hasData };
      if (hasData && categorical) properties.category = String(raw);
      if (hasData && !categorical) {
        properties.value = raw;
        properties.elevation = magnitude(layer, raw) * DISPLAY_HEIGHT_M;
      }
      return { ...feature, properties };
    }),
  };
}

// ------------------------------------------------------------------ formatting
const MINUS = '−';
const signed = (v, digits) => `${v < 0 ? MINUS : v > 0 ? '+' : ''}${Math.abs(v).toFixed(digits)}`;

export function percent(p) {
  if (!finiteNumber(p)) return 'Unavailable';
  if (p > 0 && p < 0.005) return '<1%';
  if (p < 1 && p > 0.995) return '>99%';
  return `${Math.round(p * 100)}%`;
}

export function formatValue(layer, v) {
  if (v === null || v === undefined || (typeof v === 'number' && !Number.isFinite(v))) return 'No estimate available';
  if (layer.scale.kind === 'categorical') return layer.type === 'boolean' ? (v ? 'Reviewed report available' : 'No reviewed report') : String(v);
  const unit = !layer.unit_short ? '' : layer.unit_short.startsWith('%') ? layer.unit_short : ` ${layer.unit_short}`;
  if (layer.type === 'probability') return percent(v);
  if (layer.type === 'share') return `${percent(v)}${unit}`;
  if (layer.scale.kind === 'diverging') return `${signed(v, layer.unit.includes('percentage') ? 1 : 2)}${unit}`;
  if (layer.type === 'integer') return `${v}${unit}`;
  const sign = v < 0 ? MINUS : '';
  if (layer.type === 'percentage' || layer.unit.startsWith('percent')) return `${sign}${Math.abs(v).toFixed(layer.type === 'percentage' ? 1 : 0)}${unit}`;
  const digits = Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2;
  return `${sign}${Math.abs(v).toFixed(digits)}${unit}`;
}

/** Screen-reader wording for signed numbers ("minus 0.98"), since symbols are read inconsistently. */
export const spoken = (text) => text.replace(MINUS, 'minus ').replace(/^\+/, 'plus ').replace('<1%', 'less than 1%').replace('>99%', 'more than 99%');

export function momentum(row) {
  if (!row) return null;
  const probabilities = { Closing: row.prob_gap_closing, Flat: row.prob_gap_flat, Widening: row.prob_gap_widening };
  if (!row.gap_momentum_state || Object.values(probabilities).some((p) => !finiteNumber(p))) return null;
  const likeliest = Object.entries(probabilities).reduce((a, b) => (b[1] > a[1] ? b : a))[0];
  return {
    state: row.gap_momentum_state,
    probabilities,
    likeliest,
    mismatch: likeliest !== row.gap_momentum_state,
    text: Object.entries(probabilities).map(([s, p]) => `${s} ${percent(p)}`).join(' · '),
  };
}

export function coverageText(row) {
  if (!row || !finiteNumber(row.core_domains_observed)) return 'Coverage not recorded';
  const parts = [`${row.core_domains_observed} of 4 core domains observed`];
  if (finiteNumber(row.latest_core_observation_year)) parts.push(`latest ${row.latest_core_observation_year}`);
  return parts.join(' · ');
}

const DEAD_ZONE = 0.25; // |SD| below this is described as similar rather than directional

/** Neutral sentences derived from values and metadata. Never causal, never a ranking. */
export function interpretation(row) {
  if (!row) return [];
  const lines = [];
  const gap = row.education_employment_conversion_gap_z;
  if (finiteNumber(gap)) {
    lines.push(gap > DEAD_ZONE ? 'Education outcomes are more gender-equal than employment outcomes.'
      : gap < -DEAD_ZONE ? 'Employment outcomes are more gender-equal than education outcomes.'
        : 'Education and employment outcomes show similar relative gender gaps.');
  }
  const residual = row.conversion_residual;
  if (finiteNumber(residual)) {
    lines.push(residual < -DEAD_ZONE ? "Employment opportunity is below the model's cross-validated expectation."
      : residual > DEAD_ZONE ? "Employment opportunity is above the model's cross-validated expectation. This does not by itself indicate job quality."
        : "Employment opportunity is close to the model's cross-validated expectation.");
  }
  const shortfall = row.conversion_shortfall;
  if (finiteNumber(shortfall) && shortfall > DEAD_ZONE) {
    lines.push('Over the endpoint comparison, education gender gaps improved more than employment gender gaps.');
  }
  const m = momentum(row);
  if (m) lines.push(`The model currently assigns the highest probability to a ${m.likeliest.toLowerCase()} gap (${percent(m.probabilities[m.likeliest])}).`);
  return lines;
}

// ------------------------------------------------------------------ clickable legend bins
/**
 * Turn colour stops into legend bins: each swatch owns a fixed value range whose edges are the
 * midpoints between neighbouring stops (geometric midpoints on log scales). Ranges are contiguous
 * and non-overlapping, so every value belongs to exactly one bin.
 */
export function binsFromStops(stops, fmt, { log = false } = {}) {
  const mids = stops.slice(1).map(([v], i) => (log ? Math.sqrt(stops[i][0] * v) : (stops[i][0] + v) / 2));
  return stops.map(([, color], i) => {
    const min = i === 0 ? -Infinity : mids[i - 1];
    const max = i === stops.length - 1 ? Infinity : mids[i];
    const label = min === -Infinity ? `< ${fmt(max)}` : max === Infinity ? `≥ ${fmt(min)}` : `${fmt(min)} to ${fmt(max)}`;
    return { id: `b${i}`, color, min, max, label };
  });
}

export function layerBins(layer) {
  const { kind } = layer.scale;
  if (kind === 'categorical') {
    const colors = layer.type === 'boolean' ? BOOLEAN_COLORS : STATE_COLORS;
    return Object.entries(colors).map(([category, color]) => ({ id: `c:${category}`, category, color, label: category }));
  }
  if (kind === 'stepped') {
    return scaleStops(layer).map(([v, color]) => ({ id: `b${v}`, color, min: v - 0.5, max: v + 0.5, label: String(v) }));
  }
  const fmt = (v) => formatValue({ ...layer, unit_short: '' }, v).trim();
  return binsFromStops(scaleStops(layer), fmt, { log: kind === 'log' });
}

/** Bin id for a value; 'none' when there is no estimate (missing data is its own legend row). */
export function binOf(bins, value) {
  if (value === null || value === undefined || (typeof value === 'number' && !Number.isFinite(value))) return 'none';
  if (bins[0]?.category !== undefined) return bins.find((b) => b.category === String(value))?.id ?? 'none';
  return bins.find((b) => value >= b.min && value < b.max)?.id ?? bins.at(-1).id;
}

/** Median of a layer across all economies with a value (at the same year or wave), for context. */
export function layerMedian(data, layer, year) {
  if (!data || layer.scale.kind === 'categorical') return null;
  const values = Object.keys(data.countries).map((iso) => valueFor(data, layer, iso, year)).filter(finiteNumber).sort((a, b) => a - b);
  if (!values.length) return null;
  const mid = Math.floor(values.length / 2);
  return { value: values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2, count: values.length };
}
