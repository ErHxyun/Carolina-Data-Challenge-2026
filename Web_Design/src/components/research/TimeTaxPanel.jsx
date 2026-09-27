import { useEffect, useState } from 'react';
import codes from '../../data/researchCountryCodes.json';

export default function TimeTaxPanel({ countryName, module = 'time_tax' }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(module);
  useEffect(() => {
    const controller = new AbortController();
    fetch(import.meta.env.BASE_URL + 'data/time_tax/countries.json', { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Time-use data could not load.'); return response.json(); })
      .then(setData).catch(err => { if (err.name !== 'AbortError') setError(err.message); });
    return () => controller.abort();
  }, []);
  const entry = data?.[codes[countryName]]?.[selected];
  const rows = entry?.rows || [];
  const labels = { time_tax: 'Time Tax', infrastructure: 'Infrastructure Friction', time_changes: 'Changes over time', freed_time: 'Freed time & opportunity' };
  const columns = selected === 'infrastructure'
    ? ['year', 'time_gap_hours', 'ifi_pca_z', 'electricity_gap', 'water_gap', 'cooking_gap', 'female_lfpr_pct', 'cross_source_conflict']
    : ['time_changes', 'freed_time'].includes(selected)
      ? ['year_start', 'year_end', 'delta_female_hours', 'delta_male_hours', 'delta_time_gap_hours', 'delta_female_lfpr_pp', 'freed_minutes_per_day', 'either_endpoint_flagged', 'survey_comparability']
      : ['year', 'female_unpaid_hours', 'male_unpaid_hours', 'time_gap_hours', 'female_lfpr_pct', 'cross_source_conflict'];
  return <section className="research-empty">
    <label className="research-control">National time-use analysis<select value={selected} onChange={event => setSelected(event.target.value)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <h3>{labels[selected]}</h3>
    <p>Time Tax = female − male unpaid work, in hours per day. Participation and its change use percent and percentage points respectively. These are national observations, not rural–urban estimates.</p>
    {selected === 'infrastructure' && <p>IFI PCA is standardized; a higher value indicates greater infrastructure deprivation. Access gaps use proportions.</p>}
    {['time_changes', 'freed_time'].includes(selected) && <p>First-to-last available observations. Survey comparability has not been assumed; source-conflict flags are retained.</p>}
    {error ? <p role="alert">{error}</p> : !data ? <p>Loading time-use records…</p> : !rows.length ? <p>No matching time-use records for this country.</p> :
      <div style={{ overflowX: 'auto' }}><table className="time-records"><thead><tr>{columns.filter(key => rows.some(row => key in row)).map(key => <th key={key}>{key.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{columns.filter(key => rows.some(item => key in item)).map(key => <td key={key}>{row[key] == null ? '—' : typeof row[key] === 'number' ? Number(row[key].toFixed(3)).toString() : String(row[key])}</td>)}</tr>)}</tbody></table></div>}
    {entry && <small>Source: {entry.source}</small>}
  </section>;
}
