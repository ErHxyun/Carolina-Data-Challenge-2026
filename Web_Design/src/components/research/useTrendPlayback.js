import { useEffect, useRef, useState } from 'react';

export default function useTrendPlayback(count) {
  const containerRef = useRef(null);
  const last = Math.max(0, count - 1);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [index, setIndex] = useState(() => reducedMotion ? last : 0);
  const [requested, setRequested] = useState(!reducedMotion);
  const [visible, setVisible] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [pageVisible, setPageVisible] = useState(!document.hidden);
  const playing = requested && visible && pageVisible && index < last && count > 1;

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      setReducedMotion(media.matches);
      if (media.matches) { setRequested(false); setIndex(last); }
    };
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [last]);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0.15 });
    if (containerRef.current) observer.observe(containerRef.current);
    const visibility = () => setPageVisible(!document.hidden);
    document.addEventListener('visibilitychange', visibility);
    return () => { observer.disconnect(); document.removeEventListener('visibilitychange', visibility); };
  }, []);

  useEffect(() => {
    if (!playing) return;
    // Advance through actual data years; do not invent intermediate observations.
    const timer = window.setInterval(() => setIndex((value) => Math.min(last, value + 1)), Math.max(65, 3200 / Math.max(1, last)) / speed);
    return () => window.clearInterval(timer);
  }, [playing, speed, last]);

  const select = (value) => { setRequested(false); setIndex(value); };
  const replay = () => { setIndex(0); setRequested(true); };
  const toggle = () => {
    if (index === last) replay();
    else setRequested((value) => !value);
  };
  return { containerRef, index, playing, speed, setSpeed, select, replay, toggle, showAll: () => select(last) };
}
