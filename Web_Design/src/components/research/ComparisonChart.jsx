import useTrendPlayback from './useTrendPlayback';
import { useId, useState } from 'react';
import { finite, number, segments } from './format';

export default function ComparisonChart({ title, years, rural, urban, bands, observed, unit, sourceType }) {
  const id = useId();
  const available = years.map((_, i) => i).filter((i) => finite(rural[i]) || finite(urban[i]));
  const { index: introIndex, containerRef } = useTrendPlayback(years.length);
  const introComplete = introIndex >= years.length - 1;
  const [selectedIndex, select] = useState(Math.max(0, years.length - 1));
  const index = introComplete ? selectedIndex : introIndex;
  if (!available.length) return <p className="research-empty">No values available for this series.</p>;
  const extent = [...rural, ...urban, ...(bands ? [...bands.rural_women.q05, ...bands.rural_women.q95, ...bands.urban_women.q05, ...bands.urban_women.q95] : [])].filter(finite);
  const lo = unit === '%' ? 0 : Math.min(...extent);
  const hi = unit === '%' ? 100 : Math.max(...extent);
  const span = hi - lo || 1;
  const first = years[0], last = years.at(-1);
  const x = (i) => last === first ? 320 : 52 + (years[i] - first) / (last - first) * 528;
  const y = (v) => 210 - (v - lo) / span * 164;
  const modeled = Boolean(bands);
  const intervalValue = (v) => finite(v) ? v.toFixed(2) : 'Unavailable';
  const valueText = (v) => finite(v) ? `${unit === 'relative' ? v.toFixed(2) : number(v)}${unit === '%' ? '%' : unit === 'years' ? ' years' : ' relative units'}` : 'Not available';
  const paired = available.filter((i) => finite(rural[i]) && finite(urban[i]));
  const start = paired[0], end = paired.at(-1);
  const gap = finite(rural[index]) && finite(urban[index]) ? urban[index] - rural[index] : null;
  const gapUnit = unit === '%' ? 'pp' : unit === 'years' ? 'years' : 'relative units';
  const change = paired.length > 1 ? Math.abs(urban[end] - rural[end]) - Math.abs(urban[start] - rural[start]) : null;
  return <figure ref={containerRef} className="profile-chart research-chart">
    <figcaption className="chart-heading"><div><h3>{title}</h3></div><strong>{years[index]}</strong></figcaption>
    <div className="trend-takeaway"><span>READ THE TREND</span><p>{finite(change) ? `The absolute rural–urban gap ${change === 0 ? 'was unchanged' : change < 0 ? 'narrowed' : 'widened'}${change === 0 ? '' : ` by ${Math.abs(change).toFixed(2)} ${gapUnit}`} between ${years[start]} and ${years[end]}.` : paired.length === 1 ? 'Compare the rural and urban values for the available paired year.' : 'No year has both rural and urban values; a gap cannot be calculated.'}</p></div>
    <div className="research-legend"><span className="rural-key">━ Rural women</span><span className="urban-key">┄ Urban women</span>{modeled && <span>Shading: 90% credible interval</span>}</div>
    <svg tabIndex={0} onKeyDown={event => {
      if (!introComplete) return;
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      select(current => event.key === 'Home' ? 0 : event.key === 'End' ? years.length - 1 : Math.max(0, Math.min(years.length - 1, current + (event.key === 'ArrowRight' ? 1 : -1))));
    }} viewBox="0 0 620 250" role="img" aria-label={`${title}. Rural and urban women. ${modeled ? 'Model-based relative opportunity with 90% credible intervals.' : unit} Data table available below.`}>
      <defs><clipPath id={`${id}-reveal`}><rect x="44" y="0" width={introComplete ? 560 : x(introIndex) - 44 + 7} height="250" /></clipPath></defs>
      {[0, .25, .5, .75, 1].map((f) => <g key={f}><line x1="52" x2="580" y1={y(lo + span * f)} y2={y(lo + span * f)} className="chart-gridline" />{!modeled && <text x="43" y={y(lo + span * f) + 4} textAnchor="end" className="chart-axis-label">{number(lo + span * f)}</text>}</g>)}
      {modeled && <text x="52" y="22" className="chart-axis-label">Relative opportunity · Higher = better</text>}
      {[['rural_women', rural, '#ffbd69'], ['urban_women', urban, '#6dd5e7']].map(([group, values, color]) => <g key={group} clipPath={`url(#${id}-reveal)`}>
        {bands && segments(values, (_, i) => finite(bands[group].q05[i]) && finite(bands[group].q95[i])).map((part) => <polygon key={part[0]} points={[...part.map((i) => `${x(i)},${y(bands[group].q05[i])}`), ...[...part].reverse().map((i) => `${x(i)},${y(bands[group].q95[i])}`)].join(' ')} fill={color} opacity=".12" />)}
        {segments(values, finite).map((part) => <polyline key={part[0]} points={part.map((i) => `${x(i)},${y(values[i])}`).join(' ')} fill="none" stroke={color} strokeWidth="3.5" strokeDasharray={group === 'urban_women' ? '6 4' : undefined} />)}
        {values.map((v, i) => finite(v) && <circle key={i} cx={x(i)} cy={y(v)} r={i === index ? 5 : values.length === 1 ? 5 : 2} fill={color} />)}
      </g>)}
      <line x1={x(index)} x2={x(index)} y1="40" y2="215" className="chart-crosshair" />
      {years.map((year, i) => <rect key={year} x={x(i)-Math.max(5, 264 / years.length)} y="36" width={Math.max(10, 528 / years.length)} height="180" fill="transparent" onMouseEnter={() => { if (introComplete) select(i); }} onClick={() => { if (introComplete) select(i); }}><title>{year}: rural {valueText(rural[i])}; urban {valueText(urban[i])}</title></rect>)}
      {[...new Set([0, Math.floor((years.length - 1) / 2), years.length - 1])].map((i) => <text key={i} x={x(i)} y="239" textAnchor="middle" className="chart-axis-label">{years[i]}</text>)}
    </svg>
    <div className="research-readout"><span className="rural-key">Rural women <strong>{valueText(rural[index])}</strong></span><span className="urban-key">Urban women <strong>{valueText(urban[index])}</strong></span><span>Urban − rural · {years[index]}<strong>{finite(gap) ? `${unit === 'relative' ? gap.toFixed(2) : number(gap)} ${gapUnit}` : "Not available"}</strong></span></div>
    <p className="chart-interaction-hint">Hover or tap to inspect a year · Arrow keys to move</p>
    <details className="research-table"><summary>View data table</summary>{modeled && <p className="research-caption">{sourceType}. Selected-year 90% intervals: rural {intervalValue(bands.rural_women.q05[index])}–{intervalValue(bands.rural_women.q95[index])}; urban {intervalValue(bands.urban_women.q05[index])}–{intervalValue(bands.urban_women.q95[index])}. Relative units are not percentages.</p>}{observed && <p className="research-caption">{observed[index] ? `Source observation/estimate available in ${years[index]}; lines remain model estimates.` : `No source observation in ${years[index]}; the trajectory is model-estimated.`}</p>}<div><table><thead><tr><th>Year</th><th>Rural women</th><th>Urban women</th></tr></thead><tbody>{years.map((year, i) => <tr key={year}><td>{year}</td><td>{valueText(rural[i])}</td><td>{valueText(urban[i])}</td></tr>)}</tbody></table></div></details>
  </figure>;
}
