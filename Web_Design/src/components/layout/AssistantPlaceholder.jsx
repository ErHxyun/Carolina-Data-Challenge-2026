import { useEffect, useRef, useState } from 'react';

export default function AssistantPlaceholder({ countryName }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);
  const closeRef = useRef(null);
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    function handleEscape(event) {
      if (event.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [open]);
  return <div className="assistant-shell">
    {open && <section id="assistant-preview" className="assistant-preview" role="region" aria-label="Data assistant preview">
      <header><span>Data Assistant</span><button ref={closeRef} type="button" aria-label="Close assistant" onClick={() => { setOpen(false); triggerRef.current?.focus(); }}>×</button></header>
      <span className="demo-badge">Coming later · Multi-agent workspace</span>
      <h2>A question worth exploring.</h2>
      <p>Investigate time, infrastructure, and opportunity in {countryName}.</p>
      <div className="assistant-prompts" aria-label="Example questions">
        <p>How is unpaid work shared?</p><p>Where do infrastructure gaps appear?</p><p>Does more free time coincide with more opportunity?</p>
      </div>
      <footer>Preview only. AI responses are not connected yet.</footer>
    </section>}
    <button ref={triggerRef} type="button" className="assistant-trigger" aria-expanded={open} aria-controls="assistant-preview" onClick={() => setOpen(!open)}>✦ {open ? 'Close assistant' : 'Ask Data Assistant'}</button>
  </div>;
}
