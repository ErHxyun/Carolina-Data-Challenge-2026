import { useEffect, useRef, useState } from 'react';
import { demoTopics } from '../data/mockData';
import useCountryResearch from '../components/research/useCountryResearch';
import ResearchPanel, { ResearchFacts } from '../components/research/ResearchPanel';
import { countryPortraits } from '../data/countryPortraits';
import AssistantPlaceholder from '../components/layout/AssistantPlaceholder.jsx';

export default function CountryPage({ country, initialDimension }) {
	const [topicId, setTopicId] = useState(initialDimension === 'Infrastructure' ? 'infrastructure' : ['Employment', 'Education', 'Health'].includes(initialDimension) ? 'opportunity' : 'overview');
    const research = useCountryResearch(country.name);
	const titleRef = useRef(null);
    const [photoFailed, setPhotoFailed] = useState(false);
    const portrait = countryPortraits[country.name];
    const hasPhoto = Boolean(portrait) && !photoFailed;

    function handleTabKey(event, index) {
        const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
        if (!keys.includes(event.key)) return;
        event.preventDefault();
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? demoTopics.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + demoTopics.length) % demoTopics.length;
        setTopicId(demoTopics[next].id);
        document.getElementById(`topic-${demoTopics[next].id}`)?.focus();
    }

	const topic = demoTopics.find((item) => item.id === topicId);

	useEffect(() => {
		window.scrollTo({ top: 0, behavior: 'instant' });
        titleRef.current?.focus({ preventScroll: true });
	}, []);

	return (
		<main className='country-page'>
			<aside className={`country-photo${hasPhoto ? ` has-photo${portrait.fit === "contain" ? " landscape-portrait" : ""}` : ""}`} aria-label={`Country portrait: ${country.name}`}>
                {hasPhoto && <img className="country-portrait-image" src={portrait.src} alt={portrait.alt} decoding="async" referrerPolicy="strict-origin-when-cross-origin" onError={() => setPhotoFailed(true)} />}
				<div className='photo-topline'>
					<span>Places & perspectives</span>
					<span>01 / Country portrait</span>
				</div>

				{!hasPhoto && <div className='photo-placeholder'>
					<span className='portrait-symbol' aria-hidden='true'>
						◯
					</span>
					<p>Country photograph</p>
					<span>{photoFailed ? 'Photograph unavailable' : 'Image placeholder'}</span>
				</div>}

				<div className='photo-caption'>
					<p className='eyebrow'>A closer look at</p>
					<h2>{country.name}</h2>
					{hasPhoto ? <p>{portrait.location} · Photo by <a href={portrait.source} target="_blank" rel="noreferrer">{portrait.author} / {portrait.provider} ↗</a></p> : <p>A locally relevant photograph and credit will appear here.</p>}
                    {hasPhoto && <details className="portrait-credit"><summary>Photo credits & license</summary><p>{portrait.alt}</p><a href={portrait.licenseUrl} target="_blank" rel="noreferrer">{portrait.license} ↗</a><p>{portrait.cropNote}</p></details>}
                    <span className="portrait-note">One perspective on a place. Not a portrait of every life.</span>
				</div>
			</aside>

			<div className='country-content'>
				<a href='#/' className='back-link'>
					← Back to World
				</a>

				<header className='country-header'>
					<div className='country-heading-row'>
						<p className='eyebrow'>Country profile</p>
						<span className='demo-badge'>Research preview</span>
					</div>

					<h1 ref={titleRef} tabIndex={-1}>
						{country.name}
					</h1>

					<p className='country-region'>{country.region || 'Region not provided'} <span> / Country profile</span></p>
                    <p className='country-introduction'>Everyday life. Unequal constraints. Different possibilities.</p>
				</header>

                <ResearchFacts research={research} />
                <div className='topic-navigation' role='tablist' aria-label='Analysis topics'>
					{demoTopics.map((item, index) => (
						<button key={item.id} id={`topic-${item.id}`} type='button' role='tab' aria-selected={topicId === item.id} aria-controls='country-analysis-panel' tabIndex={topicId === item.id ? 0 : -1} onKeyDown={(event) => handleTabKey(event, index)} onClick={() => setTopicId(item.id)}>
							{item.label}
						</button>
					))}
				</div>

				<section className='country-analysis' id='country-analysis-panel' role='tabpanel' aria-labelledby={`topic-${topicId}`}>
					<p className='eyebrow'>{topic.label} / An opening question</p>
					<h2>{topic.question}</h2>
					<p className='analysis-introduction'>{topic.description}</p>

                    <ResearchPanel key={topicId} topicId={topicId} research={research} initialDimension={initialDimension} />
				</section>
			</div>
            <AssistantPlaceholder countryName={country.name} />
		</main>
	);
}
