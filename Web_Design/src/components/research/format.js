export const finite = (value) => typeof value === 'number' && Number.isFinite(value);
export const number = (value) => finite(value) ? value.toFixed(1) : 'Unavailable';
export function delayText(delay, meaningful = true) {
  if (!delay || !finite(delay.median)) return 'Unavailable';
  if (!meaningful) return 'No material gap';
  return `${delay.is_lower_bound ? '> ' : ''}${number(delay.median)} years`;
}
export function intervalText(delay) {
  if (!delay) return 'No estimate available';
  if (delay.is_lower_bound) return 'Lower bound: beyond the historical comparison record';
  return `90% credible interval: ${number(delay.q05)}–${finite(delay.q95) ? number(delay.q95) : 'unbounded'} years`;
}
export function segments(values, valid) {
  const result = []; let current = [];
  values.forEach((value, index) => {
    if (valid(value, index)) current.push(index);
    else if (current.length) { result.push(current); current = []; }
  });
  if (current.length) result.push(current);
  return result;
}
