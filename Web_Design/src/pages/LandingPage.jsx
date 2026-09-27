import { useState } from 'react';
import '../styles/landing.css';

const photographs = [
	{
		id: 1,
		label: 'Voice',
		alt: 'A woman beside a chalkboard reading Women are powerful and dangerous',
		position: '30% center',
	},
	{ id: 2, label: 'Rights', alt: 'People marching with a Women’s rights are human rights sign' },
	{ id: 3, label: 'Change', alt: 'A collage of women’s suffrage and rights movements' },
	{ id: 4, label: 'Expression', alt: 'Women marching with a Women of the World Unite sign' },
	{ id: 5, label: 'Choice', alt: 'A historical collage of suffrage campaigns and marches for women’s rights' },
	{ id: 6, label: 'Possibility', alt: 'Women marching against sexism with handmade signs', position: 'center top' },
	{ id: 7, label: 'Together', alt: 'A march with a Freedom of Choice banner' },
];

export default function LandingPage({ onAskAssistant, assistantOpen }) {
	const [paused, setPaused] = useState(false);
	return (
		<main className='landing-page'>
			<section className='landing-intro' aria-labelledby='landing-title'>
				<div className='landing-heading'>
					<p className='landing-eyebrow'>Time. Access. Opportunity.</p>
					<h1 id='landing-title'>
						One world.
						<br />
						<span>Unequal possibilities.</span>
					</h1>
				</div>
				<div className='landing-invitation'>
					<p>
						Every person gets 24 hours.
						<br />
						They do not get the same 24 hours.
					</p>
					<p className='landing-description'>
						Explore how time, infrastructure, and opportunity shape women’s lives across countries.
					</p>
					<a className='landing-cta' href='#/explore'>
						Explore the data <span aria-hidden='true'>↗</span>
					</a>
					<button
						className='landing-assistant-cta'
						type='button'
						onClick={onAskAssistant}
						aria-expanded={assistantOpen}
						aria-controls='data-assistant-panel'
					>
						<span>
							Ask Data Assistant
						</span>
						<span aria-hidden='true'>→</span>
					</button>
				</div>
			</section>
			<section
				className={`landing-gallery${paused ? ' is-paused' : ''}`}
				aria-label='Perspectives on women’s voices and movements'
			>
				<div className='landing-gallery-heading'>
					<span>Many voices. A shared question.</span>
					<button
						type='button'
						onClick={() => setPaused((value) => !value)}
						aria-pressed={paused}
						className='landing-motion-control'
					>
						{paused ? 'Resume motion' : 'Pause motion'} <span aria-hidden='true'>{paused ? '▷' : 'Ⅱ'}</span>
					</button>
				</div>
				<div className='landing-gallery-window'>
					<div className='landing-gallery-track'>
						{[0, 1].map((copy) => (
							<div className='landing-gallery-group' key={copy} aria-hidden={copy === 1 ? true : undefined}>
								{photographs.map((photo) => (
									<figure className={`landing-photo landing-photo-${photo.id}`} key={photo.id}>
										<div className='landing-photo-frame'>
											<img
												src={`${import.meta.env.BASE_URL}landing/women-${String(photo.id).padStart(2, '0')}.png`}
												alt={copy === 0 ? photo.alt : ''}
												style={{ objectPosition: photo.position }}
												decoding='async'
												draggable='false'
											/>
										</div>
										<figcaption>
											<span>{photo.label}</span>
											<span>0{photo.id}</span>
										</figcaption>
									</figure>
								))}
							</div>
						))}
					</div>
				</div>
			</section>
			<footer className='landing-footer'>
				<span>A global perspective on women’s everyday realities.</span>
				<span>
					Time inequality <i aria-hidden='true'>/</i> Infrastructure <i aria-hidden='true'>/</i> Economic opportunity
				</span>
			</footer>
		</main>
	);
}
