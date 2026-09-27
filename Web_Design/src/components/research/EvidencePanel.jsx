// Reviewed evidence reports are rendered exactly as supplied; nothing is generated in the browser.

function Source({ item, note }) {
  return (
    <li>
      <p>{item.claim}</p>
      <small>
        <a href={item.url} target="_blank" rel="noopener noreferrer">{item.organization} · {item.title} ({item.publication_year ?? 'year not stated'}) ↗</a>
        {' '}· timing relative to the signal: {item.time_match}
      </small>
      {note && <p className="source-check-note" role="note">Source check: {note}</p>}
    </li>
  );
}

export default function EvidencePanel({ report, label, checks }) {
  if (!report) {
    return <p className="research-empty evidence-empty">A structured evidence review has not yet been completed for this country.</p>;
  }
  const noteFor = (url) => checks?.notes?.[url];
  const flagged = [...report.mechanisms.flatMap((m) => m.supporting_evidence), ...report.contradicting_or_complicating_evidence]
    .filter((item) => noteFor(item.url)).length;
  return (
    <details className="profile-methods evidence-panel">
      <summary>
        Reviewed evidence · overall confidence {report.overall_confidence}
        <span className="evidence-label">{label}</span>
      </summary>
      {flagged > 0 && (
        <p className="source-check-note" role="note">
          {flagged} cited source{flagged > 1 ? 's' : ''} did not match the cited document when checked on {checks.checked_on}. See the notes below.
        </p>
      )}
      <h4>Statistical signal</h4>
      <p>{report.statistical_signal.statement}</p>
      <p><small>{report.statistical_signal.period} · {report.statistical_signal.uncertainty_note}</small></p>
      <h4>Plausible mechanisms (up to three)</h4>
      <ol className="evidence-mechanisms">
        {report.mechanisms.map((m) => (
          <li key={m.mechanism}>
            <p><strong>{m.mechanism}</strong></p>
            <p><small>Confidence: {m.confidence}. {m.confidence_reason}</small></p>
            <p className="eyebrow">Supporting evidence</p>
            <ul className="evidence-sources">{m.supporting_evidence.map((item) => <Source key={item.url + item.claim} item={item} note={noteFor(item.url)} />)}</ul>
          </li>
        ))}
      </ol>
      <h4>Contradicting or complicating evidence</h4>
      {report.contradicting_or_complicating_evidence.length ? (
        <ul className="evidence-sources">{report.contradicting_or_complicating_evidence.map((item) => <Source key={item.url + item.claim} item={item} note={noteFor(item.url)} />)}</ul>
      ) : <p>None located in the review.</p>}
      <h4>Overall confidence: {report.overall_confidence}</h4>
      <p><small>Confidence rates the contextual evidence, not the probability that a mechanism caused the signal. Causal conclusion: {String(report.causal_conclusion)}.</small></p>
      <h4>Limitations</h4>
      <ul>{report.limitations.map((text) => <li key={text}>{text}</li>)}</ul>
      {report.search_summary.no_evidence_found_for.length > 0 && <>
        <h4>Not found</h4>
        <ul>{report.search_summary.no_evidence_found_for.map((text) => <li key={text}>{text}</li>)}</ul>
      </>}
    </details>
  );
}
