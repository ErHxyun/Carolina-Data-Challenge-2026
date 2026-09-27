import { useEffect, useState } from 'react';
import { loadConversionData } from '../../data/conversionResearch';

/** Shared conversion exports, fetched only once a view that needs them is opened. */
export default function useConversionResearch(enabled = true) {
  const [state, setState] = useState({ data: null, loading: true, error: '' });
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    loadConversionData()
      .then((data) => { if (active) setState({ data, loading: false, error: '' }); })
      .catch((error) => { if (active) setState({ data: null, loading: false, error: error.message }); });
    return () => { active = false; };
  }, [enabled]);
  return state;
}
