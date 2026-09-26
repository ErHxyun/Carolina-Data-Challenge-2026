import { useEffect, useState } from 'react';
import codes from '../../data/researchCountryCodes.json';
const cache = new Map();
export default function useCountryResearch(name) {
  const iso = codes[name];
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    if (!iso) return;
    let active = true;
    if (!cache.has(iso)) {
      const base = `${import.meta.env.BASE_URL}data/mia/`;
      const load = async (file) => { const response = await fetch(base + file); if (!response.ok) throw new Error('Research data could not be loaded. Please refresh to retry.'); return response.json(); };
      cache.set(iso, Promise.all([load(`${iso}.json`), load('provenance.json')]).then(([data, provenance]) => ({ data, provenance })).catch((error) => { cache.delete(iso); throw error; }));
    }
    cache.get(iso).then((result) => { if (active) setState({ ...result, loading: false }); }).catch((error) => { if (active) setState({ error: error.message, loading: false }); });
    return () => { active = false; };
  }, [iso]);
  return iso ? state : { loading: false, missing: true };
}
