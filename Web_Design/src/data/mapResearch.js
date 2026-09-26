import codes from './researchCountryCodes.json';
export const DIMENSIONS = ['Overall', 'Education', 'Employment', 'Health', 'Infrastructure'];
export const GAP_COLORS = ['#359db7', '#9cdee8', '#e4e7e9', '#ffc278', '#ec7841', '#ad382f'];
export const gapColor = ['case', ['!', ['get', 'hasData']], '#555b65',
  ['interpolate', ['linear'], ['get', 'gap'], -1.5, GAP_COLORS[0], -0.25, GAP_COLORS[1], 0, GAP_COLORS[2], 0.25, GAP_COLORS[3], 0.75, GAP_COLORS[4], 1.5, GAP_COLORS[5]]];
export function countryResearch(atlas, name) { return atlas?.countries[codes[name]]; }
export function mapData(geometry, atlas, dimension, year) {
  const index = atlas?.years.indexOf(year) ?? -1;
  return { type: 'FeatureCollection', features: geometry.features.map((feature) => {
    const value = countryResearch(atlas, feature.properties.name)?.gaps[dimension]?.[index];
    const hasData = typeof value === 'number' && Number.isFinite(value);
    return { ...feature, properties: { ...feature.properties, gap: hasData ? value : 0, hasData, year, dimension,
      elevation: hasData ? Math.abs(value) * 80000 : 0 } };
  }) };
}
