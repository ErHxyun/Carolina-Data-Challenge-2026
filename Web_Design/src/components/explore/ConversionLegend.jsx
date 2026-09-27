import { MISSING_COLOR, VALUE_TYPE_LABEL } from '../../data/conversionScale';

/**
 * Clickable legend rows shared by both map views. Each row owns a fixed value range (or category);
 * clicking it keeps only those countries highlighted, clicking again (or "Show all") clears it.
 * Other countries are dimmed, not removed, so they stay hoverable and clickable.
 */
export function LegendRows({ bins, filter, onFilter, counts }) {
  const rows = [...bins, { id: 'none', label: 'No estimate', color: MISSING_COLOR }];
  return (
    <div className='legend-filter' role='group' aria-label='Filter the map by legend range'>
      {rows.map((bin) => (
        <button
          type='button'
          key={bin.id}
          className='scene-legend-row legend-filter-row'
          aria-pressed={filter === bin.id}
          aria-label={`${bin.label}: ${counts?.[bin.id] ?? 0} countries${filter === bin.id ? ', showing only these' : ''}`}
          onClick={() => onFilter(filter === bin.id ? null : bin.id)}
        >
          <span style={{ backgroundColor: bin.color }} aria-hidden='true' />
          <em>{bin.label}</em>
          <small aria-hidden='true'>{counts?.[bin.id] ?? 0}</small>
        </button>
      ))}
      {filter && (
        <button type='button' className='legend-filter-reset' onClick={() => onFilter(null)}>
          Show all countries
        </button>
      )}
    </div>
  );
}

/** Legend for the selected conversion layer, using the existing scene-legend visual pattern. */
export default function ConversionLegend({ layer, label, bins, filter, onFilter, counts, total, children }) {
  return (
    <aside className='scene-legend conversion-legend' aria-label={`${label} legend`}>
      <p className='eyebrow'>{label}</p>
      <span className={`demo-badge value-type value-type-${layer.value_type}`}>{VALUE_TYPE_LABEL[layer.value_type]}</span>
      <LegendRows bins={bins} filter={filter} onFilter={onFilter} counts={counts} />
      <p>
        {layer.direction}.{layer.scale.kind === 'diverging' ? ' Centered at zero.' : ''}
        {layer.scale.kind === 'log' ? ' Log scale.' : ''} Click a range to show only those countries.
      </p>
      <p>Coverage: {layer.coverage} of {total} economies. {layer.caveat}</p>
      {children}
    </aside>
  );
}
