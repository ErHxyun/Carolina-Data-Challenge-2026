import { useSyncExternalStore } from 'react';
import TopNavigation from './components/layout/TopNavigation.jsx';
import WorldMap from './components/explore/CountrySceneMap.jsx';
import CountryPage from './pages/CountryPage.jsx';
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
	const hash = useSyncExternalStore(subscribeToLocation, getLocationSnapshot);

	const country = findCountry(hash);
	const invalidRoute = hash !== '#/' && !country;

	return (
		<div className={`app-shell${country ? ' country-mode' : ''}`}>
			<TopNavigation />

			<main className='page-content explore-view' hidden={Boolean(country)}>
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

				<footer className='page-footer'>
					<span>Explore / Understand / Compare</span>
				</footer>
			</main>

			{country && (
				<CountryPage
					key={country.mapKey}
					country={country}
					initialDimension={new URLSearchParams(hash.split('?')[1] || '').get('dimension')}
				/>
			)}
		</div>
	);
}
