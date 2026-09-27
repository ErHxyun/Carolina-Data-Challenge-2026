// Small, accessible visual encodings for the Conversion and Time Tax panels. Every graphic has a
// text equivalent (aria-label or adjacent text); none encodes information by colour alone.
import { STATE_COLORS, finiteNumber, percent, spoken } from '../../data/conversionScale';

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

/** Bar growing left or right from a visible zero midpoint. */
export function DivergingBar({ value, limit, label, negative = '#ffbd69', positive = '#6dd5e7' }) {
  if (!finiteNumber(value)) return <div className="viz-bar viz-empty" role="img" aria-label={`${label}: no estimate`} />;
  const share = clamp(Math.abs(value) / limit, 0, 1) * 50;
  const style = value < 0 ? { right: '50%', width: `${share}%`, background: negative } : { left: '50%', width: `${share}%`, background: positive };
  return (
    <div className="viz-bar viz-diverging" role="img" aria-label={`${label}: ${spoken(value.toFixed(2))}`}>
      <span className="viz-fill" style={style} />
      <span className="viz-zero" />
    </div>
  );
}

/** 0–1 (or 0–max) meter. */
export function Meter({ value, max = 1, label, color = '#ffbd69', marker, markerLabel }) {
  if (!finiteNumber(value)) return <div className="viz-bar viz-empty" role="img" aria-label={`${label}: no estimate`} />;
  return (
    <div className="viz-bar viz-meter" role="img" aria-label={`${label}: ${max === 1 ? percent(value) : value.toFixed(2)}${finiteNumber(marker) ? `; ${markerLabel} ${marker.toFixed(2)}` : ''}`}>
      <span className="viz-fill" style={{ width: `${clamp(value / max, 0, 1) * 100}%`, background: color }} />
      {finiteNumber(marker) && <span className="viz-marker" style={{ left: `${clamp(marker / max, 0, 1) * 100}%` }} title={markerLabel} />}
    </div>
  );
}

/** Closing / Flat / Widening probabilities as one stacked bar with labelled segments. */
export function ProbabilityBar({ probabilities }) {
  const entries = Object.entries(probabilities);
  return (
    <div className="viz-stack" role="img" aria-label={entries.map(([s, p]) => `${s} ${spoken(percent(p))}`).join(', ')}>
      {entries.map(([state, p]) => (
        <span key={state} style={{ width: `${p * 100}%`, background: STATE_COLORS[state] }} title={`${state} ${percent(p)}`} />
      ))}
    </div>
  );
}

/** n of total filled dots (data visibility). */
export function Dots({ filled, total, label }) {
  return (
    <div className="viz-dots" role="img" aria-label={`${label}: ${filled} of ${total}`}>
      {Array.from({ length: total }, (_, i) => <span key={i} className={i < filled ? 'is-on' : ''} />)}
    </div>
  );
}

/** One cell per year: filled = observed, hollow = no observation. Makes data gaps visible. */
export function YearStrip({ years, values, label }) {
  const observed = years.filter((_, i) => finiteNumber(values[i]));
  return (
    <figure className="viz-years">
      <div className="viz-year-cells" role="img" aria-label={`${label}: observed in ${observed.length} of ${years.length} years${observed.length ? `, from ${observed[0]} to ${observed.at(-1)}` : ''}`}>
        {years.map((year, i) => <span key={year} className={finiteNumber(values[i]) ? 'is-on' : ''} title={`${year}: ${finiteNumber(values[i]) ? 'observed' : 'no observation'}`} />)}
      </div>
      <figcaption><span>{years[0]}</span><span>■ observed · □ no observation</span><span>{years.at(-1)}</span></figcaption>
    </figure>
  );
}

/** Women vs men for one measure on a shared 0–100 scale. */
export function PairedBars({ rows }) {
  return (
    <div className="viz-pairs">
      {rows.map((row) => (
        <div className="viz-pair" key={row.label}>
          <div className="viz-pair-label">
            <strong>{row.label}</strong>
            <small>{row.unit} · {row.year ?? 'year not recorded'} · <span className={`value-type-chip is-${row.value_type}`}>{row.value_type === 'modelled' ? 'modelled' : 'observed'}</span></small>
          </div>
          {[['Women', row.female, 'is-women'], ['Men', row.male, 'is-men']].map(([who, v, cls]) => (
            <div className={`viz-pair-row ${cls}`} key={who}>
              <span>{who}</span>
              <div className="viz-bar viz-meter" role="img" aria-label={`${row.label}, ${who.toLowerCase()}: ${finiteNumber(v) ? `${v.toFixed(1)}` : 'not available'}`}>
                {finiteNumber(v) && <span className="viz-fill" style={{ width: `${clamp(v, 0, 100)}%` }} />}
              </div>
              <b>{finiteNumber(v) ? v.toFixed(1) : '—'}</b>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/** Compact women-vs-men rows: one line per measure, two thin bars on a shared 0–100 scale. */
export function QualityRows({ rows }) {
  return (
    <div className="q-rows">
      {rows.map((row) => (
        <div className="q-row" key={row.label}>
          <span className="q-label" title={`${row.unit} · ${row.year ?? 'year not recorded'} · ${row.value_type}`}>
            {row.label}{row.value_type === 'modelled' ? '' : ' *'}
          </span>
          {[['Women', row.female, 'is-women'], ['Men', row.male, 'is-men']].map(([who, v, cls]) => (
            <span key={who} className={`q-cell ${cls}`}>
              <span className="viz-bar viz-meter" role="img" aria-label={`${row.label}, ${who.toLowerCase()}: ${finiteNumber(v) ? v.toFixed(1) : 'not available'}`}>
                {finiteNumber(v) && <span className="viz-fill" style={{ width: `${clamp(v, 0, 100)}%` }} />}
              </span>
              <b>{finiteNumber(v) ? v.toFixed(0) : '—'}</b>
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}
