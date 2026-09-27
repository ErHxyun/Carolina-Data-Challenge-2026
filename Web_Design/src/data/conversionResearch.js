// Loads the pinned conversion exports (public/data/conversion) once and shares them across the
// map and country pages. Country names are joined through the existing researchCountryCodes.json.
import codes from './researchCountryCodes.json';
import { conversionMapData, seriesFor } from './conversionScale';

const FILES = ['snapshot_atlas', 'timeline_atlas', 'layers', 'evidence_reports', 'coverage', 'provenance'];
let pending = null;

export const isoFor = (name) => codes[name] ?? null;

export function loadConversionData() {
  if (!pending) {
    const base = `${import.meta.env.BASE_URL}data/conversion/`;
    pending = Promise.all(FILES.map(async (file) => {
      const response = await fetch(`${base}${file}.json`);
      if (!response.ok) throw new Error('Conversion research data could not be loaded. Please refresh to retry.');
      return response.json();
    }))
      .then(([snapshot, timeline, registry, evidence, coverage, provenance]) => ({
        countries: snapshot.countries,
        timeline: timeline.layers,
        layers: registry.layers,
        layerById: Object.fromEntries(registry.layers.map((layer) => [layer.id, layer])),
        evidence,
        coverage,
        provenance,
      }))
      .catch((error) => { pending = null; throw error; });
  }
  return pending;
}

export const conversionRow = (data, name) => data?.countries[isoFor(name)] ?? null;
export const evidenceReport = (data, name) => data?.evidence.reports[isoFor(name)] ?? null;
export const countrySeries = (data, layerId, name) => seriesFor(data?.timeline, layerId, isoFor(name));

export function conversionMap(geometry, data, layerId, year) {
  const layer = data?.layerById[layerId];
  return layer ? conversionMapData(geometry, data, layer, isoFor, year) : null;
}
