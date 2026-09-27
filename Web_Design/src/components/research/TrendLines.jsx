import useTrendPlayback from './useTrendPlayback';
import { useId, useState } from 'react';
import { finite } from './format';

// Every series is drawn as one continuous line, like the existing trajectory charts. Observed and
// derived series join consecutive observed years with a solid line and bridge years without an
// observation with a faint thin dotted connector (a visual link only: no value is drawn or reported
// for those years). Observed points keep dots; modelled series are dashed; derived points are
// hollow. The full history stays visible while the user inspects individual years.
// Same visual language as ComparisonChart: thick lines, solid vs dashed, small points, a large
// point for the selected year.
const STYLE = {
  observed: { dash: undefined, key: '━', note: 'observed' },
  modelled: { dash: '6 4', key: '┄', note: 'modelled estimate' },
  derived: { dash: '1 6', key: '┉', note: 'derived, same year only' },
  compiled: { dash: '10 3', key: '╌', note: 'compiled estimate' },
};

/** "Education gap moved closer to parity (−0.37 → −0.03, 1993–2021)" for the takeaway box. */
function trendSentence(s, years, show) {
  const idx = s.values.map((v, i) => (finite(v) ? i : -1)).filter((i) => i >= 0);
  if (idx.length < 2) return null;
  const a = s.values[idx[0]], b = s.values.at(idx.at(-1)) ?? s.values[idx.at(-1)];
  const change = Math.abs(b) - Math.abs(a);
  const verb = Math.abs(change) < 0.005 ? 'stayed about as far from parity' : change < 0 ? 'moved closer to parity' : 'moved further from parity';
  return `${s.label} ${verb} (${show(a)} → ${show(b)}, ${years[idx[0]]}–${years[idx.at(-1)]})`;
}

/** Pairs of neighbouring finite points; `bridged` marks a jump over years without a value. */
function links(values) {
  const idx = values.map((v, i) => (finite(v) ? i : -1)).filter((i) => i >= 0);
  return idx.slice(1).map((j, k) => ({ from: idx[k], to: j, bridged: j - idx[k] > 1 }));
}

/** Latest value at or before `index`, with its position; null if none yet. */
function lastKnown(values, index) {
  for (let i = index; i >= 0; i -= 1) if (finite(values[i])) return i;
  return null;
}

export default function TrendLines({ title, subtitle, years, series, unit, format, zero = true, axisLabel = 'Distance from parity · 0 = parity', compact = false }) {
  const id = useId();
  const { index: introIndex, containerRef } = useTrendPlayback(years.length);
  const introComplete = introIndex >= years.length - 1;
  const [selectedIndex, select] = useState(Math.max(0, years.length - 1));
  const index = introComplete ? selectedIndex : introIndex;
  const all = series.flatMap((s) => s.values).filter(finite);
  if (!all.length) return <p className="research-empty">No values available for this chart.</p>;
  const lo = Math.min(...all, zero ? 0 : Infinity), hi = Math.max(...all, zero ? 0 : -Infinity);
  const span = hi - lo || 1;
  const first = years[0], last = years.at(-1);
  const x = (i) => last === first ? 320 : 52 + ((years[i] - first) / (last - first)) * 528;
  const y = (v) => 210 - ((v - lo) / span) * 164;
  const show = format ?? ((v) => (finite(v) ? v.toFixed(2) : 'Not available'));
  const described = series.map((s) => `${s.label} (${s.kind})`).join('; ');
  const sentences = series.filter((s) => s.kind !== 'derived').map((s) => trendSentence(s, years, show)).filter(Boolean);
  return (
    <figure ref={containerRef} className={`profile-chart research-chart trend-lines${compact ? ' is-compact' : ''}`}>
      {compact ? <figcaption className="visually-hidden">{title}. {sentences.join('; ')}</figcaption> : <>
        <figcaption className="chart-heading"><div><h3>{title}</h3><p>{subtitle}</p></div><strong>{years[index]}</strong></figcaption>
        {sentences.length > 0 && <div className="trend-takeaway"><span>READ THE TREND</span><p>{sentences.join('; ')}.</p><small>Descriptive comparison of available values; not a causal statement.</small></div>}
      </>}
      <div className="research-legend">
        {series.map((s) => <span key={s.label} style={{ color: s.color }}>{STYLE[s.kind].key} {s.label} ({STYLE[s.kind].note})</span>)}
      </div>
      <svg tabIndex={0} onKeyDown={event => {
      if (!introComplete) return;
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      select(current => event.key === 'Home' ? 0 : event.key === 'End' ? years.length - 1 : Math.max(0, Math.min(years.length - 1, current + (event.key === 'ArrowRight' ? 1 : -1))));
    }} viewBox="0 0 620 250" role="img" aria-label={`${title}. ${described}. ${unit}. Data table available below.`}>
        <defs><clipPath id={`${id}-reveal`}><rect x="44" y="0" width={introComplete ? 560 : x(introIndex) - 44 + 7} height="250" /></clipPath></defs>
        {[0, 0.25, 0.5, 0.75, 1].map((f) => <line key={f} x1="52" x2="580" y1={y(lo + span * f)} y2={y(lo + span * f)} className="chart-gridline" />)}
        <text x="52" y="22" className="chart-axis-label">{axisLabel}</text>
        {zero && lo < 0 && hi > 0 && <><line x1="52" x2="580" y1={y(0)} y2={y(0)} className="chart-gridline trend-zero" /><text x="584" y={y(0) + 4} className="chart-axis-label">0</text></>}
        {series.map((s) => (
          <g key={s.label} clipPath={`url(#${id}-reveal)`}>
            {links(s.values).map(({ from, to, bridged }) => (
              <line key={from} x1={x(from)} y1={y(s.values[from])} x2={x(to)} y2={y(s.values[to])} stroke={s.color}
                strokeLinecap="round" strokeWidth="3.5" strokeOpacity={bridged ? 0.35 : 1} strokeDasharray={STYLE[s.kind].dash} />
            ))}
            {s.values.map((v, i) => finite(v) && <circle key={i} cx={x(i)} cy={y(v)} r={i === index ? 5 : 2} fill={s.color} />)}
          </g>
        ))}
        <line x1={x(index)} x2={x(index)} y1="40" y2="215" className="chart-crosshair" />
        {years.map((year, i) => (
          <rect key={year} x={x(i) - Math.max(5, 264 / years.length)} y="36" width={Math.max(10, 528 / years.length)} height="180"
            fill="transparent" onMouseEnter={() => { if (introComplete) select(i); }} onClick={() => { if (introComplete) select(i); }}>
            <title>{year}: {series.map((s) => `${s.label} ${show(s.values[i])}`).join('; ')}</title>
          </rect>
        ))}
        {[...new Set([0, Math.floor((years.length - 1) / 2), years.length - 1])].map((i) => (
          <text key={i} x={x(i)} y="239" textAnchor="middle" className="chart-axis-label">{years[i]}</text>
        ))}
      </svg>
      <div className="research-readout">
        {series.map((s) => {
          const at = finite(s.values[index]) ? index : lastKnown(s.values, index);
          return (
            <span key={s.label} style={{ color: s.color }}>
              {s.label} · {years[at ?? index]}
              <strong>{at === null ? 'No value yet' : show(s.values[at])}</strong>
            </span>
          );
        })}
      </div>
      {!compact && <p className="research-caption">{unit}. Faded line segments bridge years without a value; they are not estimates and nothing is interpolated.</p>}
    <p className="chart-interaction-hint">Hover or tap to inspect a year · Arrow keys to move</p>
    <details className="research-table"><summary>View data table</summary>{compact && <p className="research-caption">{unit}. Faded segments bridge years without a value; nothing is interpolated.</p>}<div><table>
        <thead><tr><th>Year</th>{series.map((s) => <th key={s.label}>{s.label} ({s.kind})</th>)}</tr></thead>
        <tbody>{years.map((yr, i) => series.some((s) => finite(s.values[i])) && (
          <tr key={yr}><td>{yr}</td>{series.map((s) => <td key={s.label}>{show(s.values[i])}</td>)}</tr>
        ))}</tbody>
      </table></div></details>
    </figure>
  );
}
