import { useEffect, useRef, useState } from 'react';
import '../../styles/assistant.css';

const API = (import.meta.env.VITE_AGENT_API_URL || '').replace(/\/$/, '');
async function request(path, payload, signal, onPhase) {
  if (!API && !import.meta.env.DEV) throw new Error('The assistant backend has not been connected to this deployment yet.');
  let response;
  try {
    response = await fetch(API + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error(import.meta.env.DEV
      ? 'Cannot reach the assistant API. Keep the frontend and Python backend running, then refresh this page.'
      : 'Cannot reach the assistant backend. Check the deployed API address and allowed website origin.', { cause: error });
  }
  if (![200, 400, 403, 429, 503].includes(response.status)) {
    throw new Error('Assistant API unavailable. Start the Python backend on port 8001 and retry.');
  }
  if (response.ok && onPhase) {
    if (!response.headers.get('content-type')?.includes('application/x-ndjson')) {
      throw new Error('Restart the assistant backend to enable live progress.');
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let result;
    function consume(line) {
      if (!line.trim()) return;
      const event = JSON.parse(line);
      if (event.type === 'phase') onPhase(event);
      if (event.type === 'result') result = event.report;
      if (event.type === 'error') throw new Error(event.error);
    }
    try {
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        lines.forEach(consume);
        if (done) break;
      }
      consume(buffer);
      if (!result) throw new Error('The connection ended before the report arrived. Please retry.');
      return result;
    } finally { reader.releaseLock(); }
  }
  let data;
  try { data = await response.json(); }
  catch { throw new Error('The assistant API did not return JSON. Check that the Python backend is running on port 8001.'); }
  if (!response.ok) throw new Error(data.error || 'The assistant request failed.');
  return data;
}

const PHASES = [
  { id: 'locate', title: 'Understand & locate', detail: 'Identify the country and analysis.' },
  { id: 'statistics', title: 'Statistical analysis', detail: 'Read and interpret local records.' },
  { id: 'research', title: 'Context search', detail: 'Search for cited country context.' },
  { id: 'roadmap', title: 'Policy roadmap', detail: 'Calculate target and propose implementation.' },
  { id: 'report', title: 'Report writing', detail: 'Combine statistics and available context.' },
];
const LABELS = { waiting: 'Waiting', running: 'In progress', complete: 'Complete', limited: 'Limited evidence', stopped: 'Stopped', failed: 'Failed' };
const initialPhases = () => Object.fromEntries(PHASES.map(p => [p.id, 'waiting']));
function phaseText(phases) {
  if (phases.locate === 'running') return 'Thinking · locating the country…';
  if (phases.roadmap === 'running') return 'Building policy roadmap · connecting targets, evidence and implementation…';
  if (phases.report === 'running') return 'Writing report · summarizing the available evidence…';
  if (phases.statistics === 'running' && phases.research === 'running') return 'Analyzing statistics & searching the web…';
  if (phases.research === 'running') return 'Searching the web · gathering country context…';
  if (phases.statistics === 'running') return 'Analyzing local statistics…';
  return 'Preparing the next stage…';
}

function Avatar({ user = false }) {
  return <span className={'agent-avatar' + (user ? ' is-user' : '')} aria-label={user ? 'You' : 'Data Assistant'}>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      {user ? <><circle cx="12" cy="8" r="3.5" /><path d="M5 21v-2a7 7 0 0 1 14 0v2" /></> : <><rect x="4" y="6" width="16" height="14" rx="4" /><path d="M12 3v3M1 12h3m16 0h3M8 16h8" /><circle cx="8.5" cy="11" r=".8" /><circle cx="15.5" cy="11" r=".8" /></>}
    </svg>
  </span>;
}

function PhaseCard({ id, title, phases }) {
  const state = phases[id];
  return <div className="agent-phase" data-state={state}>
    <span className="agent-phase-icon" aria-hidden="true">{state === 'complete' ? '✓' : ['limited', 'failed'].includes(state) ? '!' : state === 'running' ? '' : '·'}</span>
    <div><strong>{title}</strong><span className="agent-phase-status">{LABELS[state]}</span></div>
  </div>;
}

function Progress({ turn }) {
  return <div className="agent-progress">
    <p role="status" className={turn.busy ? 'agent-live-text' : ''}>{turn.busy ? phaseText(turn.phases) : turn.error ? 'Research interrupted' : turn.report?.status === 'complete' ? 'Report ready' : 'Report ready · limited evidence'}</p>
    <details className="agent-phase-details">
      <summary><span className="phase-show">Show phases</span><span className="phase-hide">Hide phases</span></summary>
      <div className="agent-workflow" aria-label="Research workflow: locate, parallel statistics and context search, then report" tabIndex={0}>
        <PhaseCard id="locate" title="Locate" phases={turn.phases} />
        <span className="agent-flow-arrow" aria-hidden="true">→</span>
        <div className="agent-parallel"><span className="agent-parallel-label">In parallel</span><div>
          <PhaseCard id="statistics" title="Statistics" phases={turn.phases} />
          <PhaseCard id="research" title="Web context" phases={turn.phases} />
        </div></div>
        <span className="agent-flow-arrow" aria-hidden="true">→</span>
        <PhaseCard id={turn.mode === 'policy_roadmap' ? 'roadmap' : 'report'} title={turn.mode === 'policy_roadmap' ? 'Policy roadmap' : 'Research brief'} phases={turn.phases} />
      </div>
    </details>
  </div>;
}

function Report({ report, onPlan }) {
  const [targetYear, setTargetYear] = useState(new Date().getFullYear() + 10);
  const [reduction, setReduction] = useState(50);
  const scenario = report.scenario;
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url; link.download = report.route.country_iso3 + '-' + (report.route.output_mode || 'research-brief') + '.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="agent-report">
    <small>{scenario ? 'Policy roadmap' : 'Research brief'}</small>
    <h2>{report.route.country_name}</h2>
    {scenario && <section className="agent-target"><h3>Target path · not a forecast</h3>
      {scenario.baseline != null && <p>{scenario.baseline_year} baseline: {scenario.baseline.toFixed(2)} {scenario.unit}</p>}
      {scenario.target != null && <><div className="agent-target-path"><span>{scenario.baseline_year}<br />{scenario.baseline.toFixed(2)}</span><span aria-hidden="true">⇢</span><span>{scenario.target_year} target<br />{scenario.target.toFixed(2)}</span></div><p>Required average change: {scenario.annual_change.toFixed(3)} {scenario.unit} per year, from the historical baseline.</p></>}
      {scenario.warnings.map(w => <p className="agent-warning" key={w}>{w}</p>)}
    </section>}
    {report.sections.map((section, index) => <section key={index}><h3>{section.title}</h3><p className="agent-prose">{section.text}</p><small>Evidence: {section.evidence_ids.join(', ') || 'Unavailable'}</small></section>)}
    {report.statistics.data.warnings.map(warning => <p className="agent-warning" key={warning}>{warning}</p>)}
    <details><summary>Inspect local statistical records</summary><pre>{JSON.stringify(report.statistics.data.facts, null, 2)}</pre></details>
    <details><summary>Research sources ({report.research.sources.length})</summary>
      {report.research.sources.length ? <ul>{report.research.sources.map(source => <li key={source.id}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.id}: {source.title}</a></li>)}</ul> : <p>No citation-backed web context available.</p>}
    </details>
    <small>{report.note}</small>
    {!scenario && <details><summary>Build a policy roadmap →</summary><div className="agent-target-inputs">
      <label>Target year<input type="number" min={new Date().getFullYear()+1} max="2100" value={targetYear} onChange={e => setTargetYear(Number(e.target.value))} /></label>
      <label>Gap reduction (%)<input type="number" min="0" max="100" value={reduction} onChange={e => setReduction(Number(e.target.value))} /></label>
      <button type="button" disabled={targetYear <= new Date().getFullYear() || targetYear > 2100 || reduction < 0 || reduction > 100} onClick={() => onPlan(`Build a policy roadmap for ${report.route.country_name}: reduce the ${report.route.topic.replaceAll('_', ' ')} gap by ${reduction}% by ${targetYear}.`)}>Prepare question →</button>
    </div></details>}
    <button type="button" onClick={download}>Download report ↓</button>
  </div>;
}

export default function DataAssistant({ countryName, onNavigate, open, setOpen, showTrigger = true }) {
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState([]);
  const controller = useRef(null);
  const sending = useRef(false);
  const input = useRef(null);
  const trigger = useRef(null);
  const returnFocus = useRef(null);
  const body = useRef(null);
  const followScroll = useRef(true);
  const busy = Boolean(turns.at(-1)?.busy);
  const suggestionCountry = countryName || turns.at(-1)?.report?.route.country_name || 'Armenia';
  const suggestions = [
    { label: 'Understand opportunity gaps', question: `Explain the opportunity gap for women in ${suggestionCountry}.` },
    { label: 'Explore time tax trends', question: `Explain time tax changes over time in ${suggestionCountry}.` },
    { label: 'Explore infrastructure barriers', question: `Explain infrastructure barriers for women in ${suggestionCountry}.` },
    { label: 'Build a policy roadmap', question: `How could ${suggestionCountry} halve its unpaid work gap by ${Math.max(2035, new Date().getFullYear() + 5)}? Build a policy roadmap with implementation steps.` },
  ];
  const quickQuestions = <div className="agent-quick-start">
    <p>{countryName || turns.at(-1)?.report?.route.country_name ? `Ask about ${suggestionCountry}` : 'Try an example · Armenia'}</p>
    <div className="agent-question-options" aria-label="Common questions">
      {suggestions.map(item => <button key={item.label} type="button" disabled={busy} title={item.question} onClick={() => sendQuestion(item.question)}><span>{item.label}</span><span aria-hidden="true">↗</span></button>)}
    </div>
    <small>Select a question to send it immediately.</small>
  </div>;
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { if (open) { returnFocus.current = document.activeElement; input.current?.focus(); } }, [open]);
  useEffect(() => {
    if (open && followScroll.current && body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [turns, open]);

  function submit(event) {
    event.preventDefault();
    sendQuestion(question);
  }
  async function sendQuestion(value) {
    if (!value.trim() || busy || sending.current) return;
    sending.current = true;
    const text = value.trim();
    const id = crypto.randomUUID();
    const abort = new AbortController();
    controller.current = abort;
    const timeout = setTimeout(() => abort.abort(), 240000);
    const update = values => setTurns(prev => prev.map(turn => turn.id === id ? { ...turn, ...values } : turn));
    const phases = { ...initialPhases(), locate: 'running' };
    followScroll.current = true;
    setQuestion('');
    setTurns(prev => [...prev, { id, question: text, phases: { ...phases }, busy: true, report: null, error: '' }]);
    try {
      const route = await request('/api/route', { question: text, current_country: countryName || turns.at(-1)?.report?.route.country_name }, abort.signal);
      update({ mode: route.output_mode });
      await onNavigate(route, abort.signal);
      if (abort.signal.aborted) throw new DOMException('Stopped', 'AbortError');
      phases.locate = 'complete'; update({ phases: { ...phases } });
      const report = await request('/api/report/stream', route, abort.signal, event => {
        if (PHASES.some(p => p.id === event.stage) && LABELS[event.status]) {
          phases[event.stage] = event.status;
          update({ phases: { ...phases } });
        }
      });
      update({ report, busy: false });
    } catch (error) {
      for (const key of Object.keys(phases)) if (phases[key] === 'running') phases[key] = error.name === 'AbortError' ? 'stopped' : 'failed';
      update({ busy: false, phases: { ...phases }, error: error.name === 'AbortError' ? 'Request stopped or timed out. You can send another question.' : error.message });
    } finally { clearTimeout(timeout); sending.current = false; }
  }
  function close() { setOpen(false); const target = returnFocus.current; if (target?.isConnected) target.focus(); else trigger.current?.focus(); }
  return <div className="data-assistant">
    {open && <section className="data-assistant-panel" id="data-assistant-panel" aria-label="Data Assistant" onKeyDown={event => { if (event.key === 'Escape') close(); }}>
      <header><div className="agent-header-identity"><Avatar /><div><strong>Data Assistant</strong><small>Statistics · Context · Report</small></div></div><button type="button" onClick={close} aria-label="Close assistant">×</button></header>
      <div className="data-assistant-body" ref={body} role="log" aria-label="Conversation" aria-live="polite" aria-relevant="additions" onScroll={event => { const el = event.currentTarget; followScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80; }}>
        <div className="agent-message"><Avatar /><div className="agent-bubble"><span className="agent-speaker">Data Assistant</span><p>What would you like to explore? Ask about women’s time, infrastructure, or opportunity in a country.</p>{turns.length === 0 && quickQuestions}</div></div>
        {turns.map(turn => <div className="agent-turn" key={turn.id}>
          <div className="agent-message is-user"><Avatar user /><div className="agent-bubble"><span className="agent-speaker">You</span><p>{turn.question}</p></div></div>
          <div className="agent-message"><Avatar /><div className="agent-bubble"><span className="agent-speaker">Data Assistant</span>
            <Progress turn={turn} />
            {turn.error && <p className="agent-error" role="alert">{turn.error}</p>}
            {turn.report && <Report report={turn.report} onPlan={text => { setQuestion(text); input.current?.focus(); }} />}
          </div></div>
        </div>)}
      </div>
      {turns.length > 0 && <details className="agent-more-questions"><summary>More questions · {suggestionCountry}</summary>{quickQuestions}</details>}
      <form onSubmit={submit}>
        <label htmlFor="agent-question">Message{countryName ? ' · ' + countryName : ''}</label>
        <textarea id="agent-question" ref={input} value={question} onChange={event => setQuestion(event.target.value)} maxLength={2000} rows={2} placeholder="Ask about a country…" />
        <div><small>Statistics and cited country context</small>{busy ? <button type="button" onClick={() => controller.current?.abort()}>Stop</button> : <button type="submit" disabled={!question.trim()} aria-label="Send message">Send ↑</button>}</div>
      </form>
    </section>}
    {showTrigger && <button type="button" className="data-assistant-trigger" ref={trigger} aria-expanded={open} aria-controls="data-assistant-panel" onClick={() => setOpen(!open)}>✦ {open ? 'Close assistant' : 'Ask Data Assistant'}</button>}
  </div>;
}
