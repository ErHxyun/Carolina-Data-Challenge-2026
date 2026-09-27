import { useState } from 'react';
import TrendLines from './TrendLines';
import EvidencePanel from './EvidencePanel';
import { DivergingBar, Dots, Meter, ProbabilityBar, QualityRows, YearStrip } from './ConversionVisuals';
import { conversionRow, countrySeries, evidenceReport } from '../../data/conversionResearch';
import { finiteNumber, momentum, percent, spoken } from '../../data/conversionScale';
import { shortValue } from '../../data/layerExplain';

// Compact one-screen dashboard. Three type sizes only: KPI numbers, body (13px), secondary (11.5px).
// Every number is shown once; its caption continues it in words.
// Value and its direction in one short phrase ("24.6 pp fewer women"); "No data" when missing.
const val = (id, v) => shortValue(id, v) ?? 'No data';
const MINUS = '−';

/** Standardized composites: magnitude plus who is behind. */
const composite = (v) => !finiteNumber(v) ? 'No data' : Math.abs(v) < 0.05 ? 'about level' : `${Math.abs(v).toFixed(2)} SD ${v < 0 ? 'behind' : 'ahead'}`;

function Kpi({ label, value, caption, children }) {
  return (
    <div className="cd-kpi">
      <span className="cd-label">{label}</span>
      <strong aria-label={spoken(value)}>{value}</strong>
      {children}
      {caption && <span className="cd-note">{caption}</span>}
    </div>
  );
}

function Card({ title, wide, children, aside, panel = 'summary' }) {
  return (
    <section data-panel={panel} className={`cd-card${wide ? ' is-wide' : ''}`}>
      <header><h4>{title}</h4>{aside && <span className="cd-note">{aside}</span>}</header>
      {children}
    </section>
  );
}

function Row({ label, value, bar }) {
  return (
    <div className="cd-row">
      <span className="cd-row-label">{label}</span>
      {bar}
      <b>{value}</b>
    </div>
  );
}

/** Put several timeline series on one shared year axis without filling any gaps. */
function align(entries) {
  const present = entries.filter((e) => e.series);
  if (!present.length) return null;
  const first = Math.min(...present.map((e) => e.series.years[0]));
  const last = Math.max(...present.map((e) => e.series.years.at(-1)));
  const years = Array.from({ length: last - first + 1 }, (_, i) => first + i);
  return {
    years,
    series: present.map((e) => ({ ...e, values: years.map((y) => {
      const i = e.series.years.indexOf(y);
      return i >= 0 ? e.series.values[i] : null;
    }) })),
  };
}

function Loading({ state }) {
  return <p className="research-empty" role="status">{state.loading ? 'Loading conversion research data…' : state.error}</p>;
}

function Methods({ data, notes = [] }) {
  return (
    <details className="profile-methods cd-methods">
      <summary>Sources, methods & coverage</summary>
      {notes.map((note) => <p key={note}>{note}</p>)}
      <p>Model outputs (conversion gap, residual, shortfall, momentum states and first-passage probabilities) come from the team's conversion analysis. Residuals are investigation triggers, not causal effects; HMM states and first-passage values are conditional model probabilities, not forecasts or promises.</p>
      <p>Historical series come from World Bank archives: UNESCO enrollment (observed, with gaps), ILO modelled labour estimates, and Findex/ID4D survey waves. Missing years are not filled; combined values use same-year pairs only. Missing data are not zero. * = observed statistics; other work measures are ILO modelled estimates.</p>
      <p>Built {data.provenance.generated_at?.slice(0, 10)} · raw archive commit {data.provenance.inputs.raw_archive.commit.slice(0, 7)}.</p>
      <a href={`${import.meta.env.BASE_URL}data/conversion/LAYER_NOTES.md`} target="_blank" rel="noopener noreferrer">Layer notes ↗</a>{' '}
      <a href={`${import.meta.env.BASE_URL}data/conversion/provenance.json`} target="_blank" rel="noopener noreferrer">Provenance ↗</a>
    </details>
  );
}

export function ConversionPanel({ countryName, state }) {
  const [view, setView] = useState('summary');
  if (!state.data) return <Loading state={state} />;
  const data = state.data;
  const r = conversionRow(data, countryName);
  const layer = (id) => data.layerById[id];
  const report = evidenceReport(data, countryName);
  if (!r) {
    return <>
      <p className="research-empty">No conversion estimates are available for this country or territory. Values are not imputed from other countries.</p>
      <EvidencePanel report={report} label={data.evidence.label} checks={data.evidence.source_checks} />
    </>;
  }
  const m = momentum(r);
  const history = align([
    { label: 'Education gap', kind: 'observed', color: '#6dd5e7', series: countrySeries(data, 'education_gap_timeline', countryName) },
    { label: 'Employment gap', kind: 'modelled', color: '#ffbd69', series: countrySeries(data, 'employment_gap_timeline', countryName) },
    { label: 'Conversion gap', kind: 'derived', color: '#eaa0c3', series: countrySeries(data, 'conversion_gap_timeline', countryName) },
  ]);
  const eduSeries = countrySeries(data, 'education_gap_timeline', countryName);
  const eduYears = Array.from({ length: 2024 - 1990 + 1 }, (_, i) => 1990 + i);
  const eduObserved = eduYears.map((y) => {
    const i = eduSeries ? eduSeries.years.indexOf(y) : -1;
    return i >= 0 ? eduSeries.values[i] : null;
  });
  const quality = (r.employment_quality ?? []).filter((q) => !q.label.includes('enrollment'));
  const finance = layer('finance_gender_gap_pp'), digital = layer('digital_gender_gap_pp');
  const nSupporting = report?.mechanisms.reduce((n, mm) => n + mm.supporting_evidence.length, 0);

  return <div className="cd conversion-workspace" data-view={view}>
    <div className="analysis-view-switch" role="group" aria-label="Conversion view">
      {['summary','trends','quality','evidence','methods'].map(id => <button key={id} type="button" aria-pressed={view === id} onClick={() => setView(id)}>{id === 'quality' ? 'Work & coverage' : id[0].toUpperCase() + id.slice(1)}</button>)}
    </div>
    <div className="cd-kpis" aria-label="Conversion summary">
      <Kpi label="Education vs work equality" value={val('education_employment_conversion_gap_z', r.education_employment_conversion_gap_z)}>
        <DivergingBar value={r.education_employment_conversion_gap_z} limit={layer('education_employment_conversion_gap_z').scale.domain[2]} label="Education ahead of employment" negative="#b8911f" positive="#eaa0c3" />
      </Kpi>
      <Kpi label="Women's work vs model" value={val('conversion_residual', r.conversion_residual)}>
        <DivergingBar value={r.conversion_residual} limit={layer('conversion_residual').scale.domain[2]} label="Conversion surprise" negative="#c2562d" positive="#2f7fa0" />
      </Kpi>
      <Kpi label="Direction of change" value={m ? m.state : 'No data'} caption={m?.text}>
        {m && <ProbabilityBar probabilities={m.probabilities} />}
      </Kpi>
      <Kpi label="Chance gap persists 15 yrs" value={val('prob_gap_not_halved_within_15y', r.prob_gap_not_halved_within_15y)}>
        <Meter value={r.prob_gap_not_halved_within_15y} label="Chance the gap persists" color="#c2477f" />
      </Kpi>
      <Kpi label="Core areas with data" value={`${r.core_domains_observed ?? 0} of 4`}>
        <Dots filled={r.core_domains_observed ?? 0} total={4} label="Core domains observed" />
      </Kpi>
    </div>

    {m?.mismatch && <p className="cd-reading cd-note">Labelled state {m.state} differs from the most probable state ({m.likeliest}).</p>}

    <div className="cd-grid">
      {view === 'trends' && history && <Card panel="trends" title="Education vs employment over time" aside="0 = gender parity">
        <TrendLines compact title="Education and employment gaps over time" subtitle="Distance from gender parity"
          years={history.years} series={history.series}
          unit="Parity points: education = secondary enrollment GPI − 1 (UNESCO, observed); employment = labour-force participation ratio − 1 (ILO modelled); conversion = education − employment, same year only"
          format={(v) => (finiteNumber(v) ? `${v < 0 ? MINUS : ''}${Math.abs(v).toFixed(2)}` : 'No value')} />
      </Card>}

      <Card title="Gaps today" aside="◀ women behind · ahead ▶">
        <Row label="Education" value={composite(r.education_gender_gap_z)}
          bar={<DivergingBar value={r.education_gender_gap_z} limit={4} label="Education gap" />} />
        <Row label="Employment" value={composite(r.employment_gender_gap_z)}
          bar={<DivergingBar value={r.employment_gender_gap_z} limit={4} label="Employment gap" />} />
        <Row label="Bank account" value={val('finance_gender_gap_pp', r.finance_gender_gap_pp)}
          bar={<DivergingBar value={r.finance_gender_gap_pp} limit={finance.scale.domain[2]} label="Bank account gap" />} />
        <Row label="Internet" value={val('digital_gender_gap_pp', r.digital_gender_gap_pp)}
          bar={<DivergingBar value={r.digital_gender_gap_pp} limit={digital.scale.domain[2]} label="Digital access gap" />} />
        <Row label="Women with ID" value={val('identity_female_pct', r.identity_female_pct)}
          bar={<Meter value={finiteNumber(r.identity_female_pct) ? r.identity_female_pct / 100 : null} label="Women with official ID" color="#6dd5e7" />} />
        <Row label="Extra unpaid care" value={finiteNumber(r.time_tax_extra_hours_day) ? `${r.time_tax_extra_hours_day.toFixed(1)} h/day` : 'No data'}
          bar={<Meter value={r.time_tax_extra_hours_day} max={5} label="Extra unpaid hours per day" color="#eaa0c3" />} />
      </Card>

      {quality.length > 0 && <Card panel="quality" title="Access vs quality of work" aside="women / men, %">
        <QualityRows rows={quality} />
      </Card>}

      <Card panel="quality" title="What the data can see" aside="education records, 1990–2024">
        <YearStrip years={eduYears} values={eduObserved} label="Observed secondary-enrollment parity, 1990–2024" />
        <p className="cd-body">
          Measured in <b>{r.observed_education_years} of 35</b> years · latest <b>{r.latest_observed_education_year ?? 'none'}</b> · <b>{percent(r.observed_missing_share)}</b> of gender records missing.
        </p>
      </Card>

      <Card panel="evidence" title="Contextual evidence — not causal attribution" wide={Boolean(report)}>
        {report && <div className="viz-evidence-chips" aria-label="Evidence review summary">
          <span className={`chip is-${report.overall_confidence}`}>Confidence: {report.overall_confidence}</span>
          <span className="chip">{report.mechanisms.length} mechanisms</span>
          <span className="chip">{nSupporting} supporting</span>
          <span className="chip">{report.contradicting_or_complicating_evidence.length} complicating</span>
        </div>}
        <EvidencePanel report={report} label={data.evidence.label} checks={data.evidence.source_checks} />
      </Card>
    </div>
    <Methods data={data} notes={[
      'Exploratory model signals, not causal findings. Education and employment measures can cover different cohorts and years.',
      `Survey years: bank account ${r.finance_gender_gap_year ?? '—'}, ID ${r.identity_female_pct_year ?? '—'}, time use ${r.time_tax_year ?? 'none'}. Work measures are shown separately and never combined into a score; * = observed, others ILO modelled.`,
    ]} />
  </div>;
}

export function TimeTaxPanel({ countryName, state }) {
  if (!state.data) return <Loading state={state} />;
  const data = state.data;
  const r = conversionRow(data, countryName);
  const infra = align([
    { label: 'Electricity gap', kind: 'compiled', color: '#ffbd69', series: countrySeries(data, 'rural_electricity_gap_timeline', countryName) },
    { label: 'Clean-cooking gap', kind: 'modelled', color: '#6dd5e7', series: countrySeries(data, 'rural_clean_cooking_gap_timeline', countryName) },
  ]);
  const direct = finiteNumber(r?.time_tax_extra_hours_day);
  const context = finiteNumber(r?.rural_time_tax_gap_latest_pp);
  if (!direct && !context && !infra) {
    return <p className="research-empty">No time-use or rural infrastructure data are available for this country or territory. Missing data are not zero.</p>;
  }
  const all = Object.values(data.countries).map((c) => c.time_tax_extra_hours_day).filter(finiteNumber).sort((a, b) => a - b);
  const median = all.length ? all[Math.floor(all.length / 2)] : null;
  return <div className="cd">
    <div className="cd-kpis" aria-label="Time tax summary">
      <Kpi label="Extra unpaid care, women vs men" value={direct ? `${r.time_tax_extra_hours_day.toFixed(1)} h/day` : 'No data'}>
        {direct && <Meter value={r.time_tax_extra_hours_day} max={5} label="Extra unpaid hours per day" color="#eaa0c3" marker={median} markerLabel={`median of ${all.length} economies`} />}
      </Kpi>
      <Kpi label="Rural services gap" value={context ? val('rural_time_tax_gap_latest_pp', r.rural_time_tax_gap_latest_pp) : 'No data'} />
      <Kpi label="Rural gap trend" value={r?.rural_time_tax_gap_trend ?? 'No data'} />
      <Kpi label="Chance rural gap shrinks" value={finiteNumber(r?.prob_rural_time_tax_gap_shrinking) ? percent(r.prob_rural_time_tax_gap_shrinking) : 'No data'} />
    </div>
    {infra && <div className="cd-grid">
      <Card title="Rural–urban access gaps over time" wide aside="higher = rural further behind">
        <TrendLines compact title="Rural–urban access gaps over time" subtitle="Urban minus rural access" years={infra.years} series={infra.series}
          axisLabel="Urban − rural access gap (pp)" zero
          unit="Percentage points (urban − rural): electricity = SDG7 compiled estimates; clean cooking = WHO modelled estimates"
          format={(v) => (finiteNumber(v) ? `${v < 0 ? MINUS : ''}${Math.abs(v).toFixed(1)} pp` : 'No value')} />
      </Card>
    </div>}
    <Methods data={data} notes={[
      `Unpaid care: time-use survey ${r?.time_tax_year ?? 'not available'}; only ${all.length} economies have one${median ? `, median ${median.toFixed(1)} h/day (the line on the bar)` : ''}. Missing data are not zero.`,
      'Rural services gaps are household context, not a women-only outcome, and are never combined with the gendered time-use value.',
    ]} />
  </div>;
}
