import { useState } from 'react';
import ComparisonChart from './ComparisonChart';
import { delayText, intervalText, finite, number } from './format';
import { ConversionPanel, TimeTaxPanel } from './ConversionPanel';

export function ResearchFacts({ research }) {
  if (!research.data) return <p className="research-empty" role="status">{research.loading ? 'Loading research data…' : research.error || 'Research data is not available for this country or territory.'}</p>;
  const s = research.data.summary, d = s.delay_2021?.Overall, progress = s.progress_2010_2020?.Overall;
  return <div className="profile-facts research-facts" aria-label="Research summary">
    <div><span>Opportunity Delay · 2021</span><strong>{delayText(d, s.meaningful_gap)}</strong><small>{s.meaningful_gap ? intervalText(d) : 'Delay is not ranked without a material gap.'}</small></div>
    <div><span>Progress · 2010–2020</span><strong>{progress?.label || 'Unavailable'}</strong><small>{progress && progress.label === 'Converging progress' ? `${Math.round(progress.p_converging * 100)}% posterior probability` : 'Model-based classification'}</small></div>
    <div><span>Country evidence</span><strong>{research.data.indicators.length} indicators</strong><small>Coverage varies by indicator and year.</small></div>
  </div>;
}

function IndicatorExplorer({ indicators, dimensions }) {
  const options = indicators.filter((i) => dimensions.includes(i.dimension));
  const [selected, setSelected] = useState('');
  const item = options.find((i) => i.indicator === selected) || options[0];
  if (!item) return <p className="research-empty">No interpretable indicators available for these dimensions.</p>;
  return <section className="indicator-explorer"><label className="research-control">Indicator<select value={item.indicator} onChange={(e) => setSelected(e.target.value)}>{options.map((i) => <option key={i.indicator} value={i.indicator}>{i.label}</option>)}</select></label>
    <ComparisonChart key={item.indicator} title={item.label} years={item.years} rural={item.rural_women} urban={item.urban_women} unit={item.unit} sourceType={item.source_type} />
  </section>;
}

export default function ResearchPanel({ topicId, research, initialDimension, conversion, countryName }) {
  const [view, setView] = useState('trend');
  const [dimension, setDimension] = useState(topicId === 'infrastructure' ? 'Infrastructure' : topicId === 'opportunity' ? (['Employment', 'Education', 'Health'].includes(initialDimension) ? initialDimension : 'Employment') : 'Overall');
  if (topicId === 'conversion') return <ConversionPanel countryName={countryName} state={conversion} />;
  if (topicId === 'time' && conversion && !conversion.error) return <TimeTaxPanel countryName={countryName} state={conversion} />;
  if (topicId === 'time') return <div className="research-empty"><h3>Time Tax analysis is not connected yet.</h3><p>This module will use the team's unpaid-work and time-use analysis. Mia's Opportunity Delay measures years of trajectory difference, not hours of unpaid work.</p></div>;
  if (!research.data) return <p className="research-empty" role="status">{research.loading ? 'Loading research data…' : research.error || 'No matching research data. Values are not imputed from other countries.'}</p>;
  const { summary: s, years, trajectories, indicators } = research.data;
  const dims = topicId === 'opportunity' ? ['Employment', 'Education', 'Health'] : [dimension];
  const trajectory = trajectories[dimension];
  const delay = s.delay_2021?.[dimension];
  const progress = s.progress_2010_2020?.[dimension];
  const half = s.half_life?.[dimension];
  const sparse = finite(delay?.years_to_nearest_obs) && delay.years_to_nearest_obs > 5;
  return <div className="research-workspace">
    <div className="analysis-view-switch" role="group" aria-label="Analysis view">
      {[['trend','Trend'],['indicators','Indicators'],['findings','Findings'],['methods','Methods']].map(([id,label]) => <button type="button" key={id} aria-pressed={view === id} onClick={() => setView(id)}>{label}</button>)}
    </div>
    <div className="analysis-view-body">
    {topicId === 'opportunity' && <label className="research-control">Dimension<select value={dimension} onChange={(e) => setDimension(e.target.value)}>{dims.map((d) => <option key={d}>{d}</option>)}</select></label>}
    {view === 'findings' && <><div className={`research-callout${sparse ? ' sparse-evidence' : ''}`}>
      <p className="eyebrow">{dimension} / Opportunity Delay / 2021</p><h3>{delayText(delay, s.meaningful_gap)}</h3>
      {sparse && <p>Limited nearby observations: the closest source observation is {delay.years_to_nearest_obs} years from 2021. Interpret this estimate cautiously.</p>}
    </div>
    <div className="analysis-notes"><article><p className="eyebrow">01 / Progress / 2010–2020</p><h3>{progress?.label || 'Unavailable'}</h3><p>{progress && !['Insufficient data', 'At parity'].includes(progress.label) ? `Posterior probability of converging progress: ${Math.round(progress.p_converging * 100)}%. Probability of progress without convergence: ${Math.round(progress.p_pwc * 100)}%.` : 'There is insufficient evidence for a directional progress statement, or the groups are at parity.'}</p></article>
    <article><p className="eyebrow">02 / Gap half-life</p><h3>{half?.verdict || 'Unavailable'}</h3><p>{half?.verdict === 'Converging' ? `Estimated half-life: ${number(half.median)} years. ${intervalText(half)}. This summarizes the fitted historical convergence rate, not a promised future date.` : 'A numeric half-life is not shown without sufficient evidence of convergence.'}</p></article></div>
    </>}
    {view === 'trend' && <>
    {trajectory ? <ComparisonChart key={`trajectory-${dimension}`} title={`${dimension}: rural and urban women`} years={years} rural={trajectory.rural_women.median} urban={trajectory.urban_women.median} bands={trajectory} observed={trajectory.observed_year} unit="relative" sourceType="Bayesian model estimates" /> : <p className="research-empty">No modelled trajectory available for {dimension.toLowerCase()}.</p>}
    </>}
    {view === 'indicators' && <><h3 className="research-section-title">Explore the underlying indicators</h3>
    <IndicatorExplorer key={`indicators-${dimension}`} indicators={indicators} dimensions={topicId === 'overview' ? ['Education','Employment','Health','Infrastructure','Finance','Digital','Resilience'] : dimension === 'Infrastructure' ? ['Infrastructure','Health'] : [dimension]} />
    </>}
    {view === 'methods' && <details open className="profile-methods"><summary>Sources, methods & coverage</summary>{delay && s.meaningful_gap && <p>{dimension} delay: {intervalText(delay)}. Rural women's modelled trajectory resembles urban women's trajectory {delay.is_lower_bound ? 'more than ' : ''}{number(delay.median)} years earlier; this is a trajectory comparison, not an individual woman's age or years of unpaid work.</p>}{!s.meaningful_gap && <p>A delay ranking is not meaningful where the overall gap is below the material-gap threshold.</p>}<p>Trend statements compare model medians; shading shows 90% credible intervals. Indicator charts: estimated series approximate rural and urban women from separate area and sex statistics; household series apply to women and men in the same area.</p><p>World Bank Indicators API datasets, analysed in Mia's research pipeline: Gender Statistics, World Development Indicators, Global Jobs Indicators Database, Global Findex and Identification for Development.</p><p>Most rural-women series are model-based approximations. Three indicators are direct measurements; household infrastructure values apply equally to women and men within an area. Missing observations are not zeros.</p><p>The latent scale expresses relative opportunity, not percentages. Shading shows 90% credible intervals. Finance, Digital and Resilience are 2024 snapshots. The 2D/3D map uses national model gaps, not subnational observations. Time-use research remains a separate module.</p><a href={`${import.meta.env.BASE_URL}data/mia/DATA_DICTIONARY.md`} target="_blank" rel="noreferrer">Read data dictionary ↗</a><p><a href={research.provenance.sourceUrl} target="_blank" rel="noreferrer">Mia research export · {research.provenance.commit.slice(0,7)} ↗</a></p></details>}
    </div>
  </div>;
}
