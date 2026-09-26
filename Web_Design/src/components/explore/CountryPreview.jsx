export default function CountryPreview({ country, onClose }) {
	return (
		<aside className='country-preview' aria-label='Selected country'>
			<div className='preview-heading'>
				<div>
					<p className='eyebrow'>Country preview</p>
					<h2>{country.name}</h2>
				</div>

				<button className='preview-close' type='button' onClick={onClose} aria-label='Close country preview'>
					×
				</button>
			</div>

			<span className='demo-badge'>Analysis placeholder</span>

			<dl className='preview-metrics'>
				<div>
					<dt>Time inequality</dt>
					<dd>—</dd>
				</div>
				<div>
					<dt>Infrastructure</dt>
					<dd>—</dd>
				</div>
				<div>
					<dt>Opportunity</dt>
					<dd>—</dd>
				</div>
			</dl>

			<p className='preview-description'>
				Explore how everyday life and economic opportunity connect. Country analysis and interactive charts will appear
				here.
			</p>

			<a className='preview-cta' href={`#/country/${encodeURIComponent(country.name)}`}>
				Explore more →
			</a>
		</aside>
	);
}
