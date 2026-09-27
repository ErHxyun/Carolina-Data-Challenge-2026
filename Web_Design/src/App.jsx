import { useState, useSyncExternalStore } from 'react';
import DataAssistant from './components/layout/DataAssistant.jsx';
import TopNavigation from './components/layout/TopNavigation.jsx';
import WorldMap from './components/explore/CountrySceneMap.jsx';
import CountryPage from './pages/CountryPage.jsx';
import LandingPage from './pages/LandingPage.jsx';
import { countryOptions } from './data/worldGeometry';

function subscribeToLocation(callback) {
	window.addEventListener('hashchange', callback);

	return () => {
		window.removeEventListener('hashchange', callback);
	};
}

function getLocationSnapshot() {
	return window.location.hash || '#/';
}

function findCountry(hash) {
	if (!hash.startsWith('#/country/')) return null;

	try {
		const name = decodeURIComponent(hash.slice('#/country/'.length).split('?')[0]);
		return countryOptions.find((country) => country.name === name) ?? null;
	} catch {
		return null;
	}
}

export default function App() {
	const [assistantOpen, setAssistantOpen] = useState(false);
	const hash = useSyncExternalStore(subscribeToLocation, getLocationSnapshot);

	const country = findCountry(hash);
	const landing = hash === '#/';
	const invalidRoute = !landing && hash !== '#/explore' && !country;

	return (
		<div className={`app-shell${country ? ' country-mode' : ''}`}>
			<TopNavigation />
			{landing && <LandingPage onAskAssistant={() => setAssistantOpen(true)} assistantOpen={assistantOpen} />}

			<main className='page-content explore-view' hidden={landing || Boolean(country)}>
				<header>
					<h1 className='page-title'>A world of different realities.</h1>

					<p className='page-description'>
						Explore how opportunity, infrastructure, and everyday life differ across countries.
					</p>

					{invalidRoute && (
						<p role='status' className='page-description'>
							This page could not be found. Select a country on the map.
						</p>
					)}
				</header>

				<WorldMap />
			</main>

			{country && (
				<CountryPage
					key={hash}
					country={country}
					initialAnalysis={new URLSearchParams(hash.split('?')[1] || '').get('analysis')}
					initialTopic={new URLSearchParams(hash.split('?')[1] || '').get('topic')}
					initialDimension={new URLSearchParams(hash.split('?')[1] || '').get('dimension')}
				/>
			)}
			<DataAssistant
				open={assistantOpen}
				setOpen={setAssistantOpen}
				showTrigger={!landing}
				countryName={country?.name}
				onNavigate={async (route, signal) => {
					const target = countryOptions.find((item) => item.name === route.country_name);
					if (!target) return;
					window.location.hash = '/explore';
					await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
					if (signal?.aborted) return;
					window.dispatchEvent(new CustomEvent('agent:navigate', { detail: { ...route, mapKey: target.mapKey } }));
					await new Promise((resolve) =>
						setTimeout(resolve, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1200),
					);
					if (signal?.aborted || window.location.hash !== '#/explore') return;
					const topic = ['time_tax', 'time_changes', 'freed_time'].includes(route.topic)
						? 'time'
						: route.topic === 'infrastructure'
							? 'infrastructure'
							: route.dimension === 'Overall'
								? 'overview'
								: 'opportunity';
					window.location.hash =
						'/country/' +
						encodeURIComponent(target.name) +
						'?dimension=' +
						encodeURIComponent(route.dimension) +
						'&topic=' +
						topic +
						'&analysis=' +
						route.topic;
				}}
			/>
		</div>
	);
}
