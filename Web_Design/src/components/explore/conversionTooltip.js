// Content for the existing MapLibre country popup in conversion mode. Built with textContent only,
// so data values can never inject markup.
import { VALUE_TYPE_LABEL, coverageText, formatValue, momentum, observationYear, valueFor } from '../../data/conversionScale';
import { explainValue } from '../../data/layerExplain';

function line(parent, text, className) {
  const el = document.createElement(className === 'tooltip-title' ? 'strong' : 'span');
  el.className = className;
  el.textContent = text;
  parent.append(el);
}

export function conversionTooltip(name, iso, data, layer, year) {
  const root = document.createElement('div');
  root.className = 'conversion-tooltip';
  line(root, name, 'tooltip-title');
  const row = iso ? data.countries[iso] : null;
  const value = valueFor(data, layer, iso, year);
  const m = layer.id === 'gap_momentum_state' ? momentum(row) : null;
  if (m) {
    line(root, `${layer.display_label}: ${m.state}`, 'tooltip-value');
    line(root, m.text, 'tooltip-detail');
    if (m.mismatch) line(root, `Highest-probability state: ${m.likeliest}`, 'tooltip-detail');
  } else {
    line(root, layer.display_label, 'tooltip-label');
    const explained = explainValue(layer.id, value);
    line(root, explained ? explained.headline : formatValue(layer, value), 'tooltip-value');
    if (explained) line(root, explained.caption, 'tooltip-explain');
  }
  const obs = observationYear(data, layer, iso, year);
  if (layer.temporal === 'snapshot') line(root, obs ? `Observed ${obs}` : layer.period, 'tooltip-detail');
  else if (value === null || value === undefined) line(root, `No observation in ${year === 'latest' ? 'any wave' : year}`, 'tooltip-detail');
  else line(root, `${layer.temporal === 'waves' ? 'Survey wave' : 'Year'} ${obs ?? year}`, 'tooltip-detail');
  line(root, `${VALUE_TYPE_LABEL[layer.value_type]} · ${iso ? coverageText(row) : 'Not in the conversion dataset'}`, 'tooltip-detail');
  line(root, layer.short_caveat, 'tooltip-caveat');
  return root;
}
