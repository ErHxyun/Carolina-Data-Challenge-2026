import { useEffect, useRef, useState } from 'react';
import { Map, NavigationControl, Popup, setWorkerUrl } from 'maplibre-gl';

import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

import { countryOptions, worldGeometry } from '../../data/worldGeometry';
import CountryPreview from './CountryPreview.jsx';

setWorkerUrl(workerUrl);

export default function WorldMap() {
	const containerRef = useRef(null);
	const mapRef = useRef(null);

	const [ready, setReady] = useState(false);
	const [error, setError] = useState('');
	const [selectedCountry, setSelectedCountry] = useState(null);

	useEffect(() => {
		let map;

		try {
			map = new Map({
				container: containerRef.current,
				style: {
					version: 8,
					sources: {},
					layers: [
						{
							id: 'background',
							type: 'background',
							paint: { 'background-color': '#101012' },
						},
					],
				},
				bounds: [
					[-180, -60],
					[180, 85],
				],

				fitBoundsOptions: {
					padding: {
						top: 48,
						bottom: 64,
						left: 72,
						right: 72,
					},
					duration: 0,
				},

				minZoom: -2,
				maxZoom: 6,
				renderWorldCopies: false,

				// Allow space around a single world instead of forcing it to fill the width.
				transformConstrain: (center, zoom) => ({
					center: {
						lng: Math.max(-180, Math.min(180, center.lng)),
						lat: Math.max(-85, Math.min(85, center.lat)),
					},
					zoom: Math.max(-2, Math.min(6, zoom)),
				}),

				attributionControl: {
					compact: true,
					customAttribution:
						'Boundaries: <a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener noreferrer">Natural Earth</a>',
				},
			});
		} catch {
			// Report an external map initialization failure to the UI.
			// eslint-disable-next-line react-hooks/set-state-in-effect
			setError('The map could not start. Check browser WebGL support.');
			return;
		}

		mapRef.current = map;

		map.addControl(new NavigationControl({ showCompass: false }), 'top-left');

		map.dragRotate.disable();
		map.touchZoomRotate.disableRotation();

		const tooltip = new Popup({
			closeButton: false,
			closeOnClick: false,
			offset: 12,
			className: 'country-tooltip',
		});

		map.on('error', () => {
			setError('The map could not load. Please refresh the page.');
		});

		map.on('load', () => {
			map.addSource('countries', {
				type: 'geojson',
				data: worldGeometry,
			});

			map.addLayer({
				id: 'country-fill',
				type: 'fill',
				source: 'countries',
				paint: {
					'fill-color': '#28282c',
					'fill-opacity': 1,
				},
			});

			map.addLayer({
				id: 'country-borders',
				type: 'line',
				source: 'countries',
				paint: {
					'line-color': '#55555e',
					'line-width': 0.6,
				},
			});

			map.addLayer({
				id: 'country-selected',
				type: 'line',
				source: 'countries',
				filter: ['==', ['get', 'mapKey'], ''],
				paint: {
					'line-color': '#f2f0eb',
					'line-width': 2,
				},
			});

			map.on('mousemove', 'country-fill', (event) => {
				const country = event.features?.[0];
				if (!country) return;

				map.getCanvas().style.cursor = 'pointer';

				tooltip.setLngLat(event.lngLat).setText(country.properties.name).addTo(map);
			});

			map.on('mouseleave', 'country-fill', () => {
				map.getCanvas().style.cursor = '';
				tooltip.remove();
			});

			map.on('click', 'country-fill', (event) => {
				const country = event.features?.[0];
				if (!country) return;

				tooltip.remove();

				setSelectedCountry({
					mapKey: country.properties.mapKey,
					name: country.properties.name,
				});
			});

			setReady(true);
		});

		const resizeObserver = new ResizeObserver(() => map.resize());
		resizeObserver.observe(containerRef.current);

		return () => {
			resizeObserver.disconnect();
			tooltip.remove();
			map.remove();
			mapRef.current = null;
		};
	}, []);

	useEffect(() => {
		const map = mapRef.current;
		if (!ready || !map?.getLayer('country-selected')) return;

		const selectedKey = selectedCountry?.mapKey ?? '';

		map.setFilter('country-selected', ['==', ['get', 'mapKey'], selectedKey]);

		map.setPaintProperty('country-fill', 'fill-color', [
			'case',
			['==', ['get', 'mapKey'], selectedKey],
			'#64646d',
			'#28282c',
		]);
	}, [ready, selectedCountry]);

	function handleCountryChange(event) {
		const country = countryOptions.find((item) => item.mapKey === event.target.value);

		setSelectedCountry(country ?? null);
	}

	return (
		<section className='map-section' aria-label='Explore countries'>
			<div className='map-toolbar'>
				<label className='country-select-label'>
					<span>Explore a country</span>

					<select
						value={selectedCountry?.mapKey ?? ''}
						onChange={handleCountryChange}
						disabled={!ready || Boolean(error)}
					>
						<option value=''>Select a country</option>

						{countryOptions.map((country) => (
							<option key={country.mapKey} value={country.mapKey}>
								{country.name}
							</option>
						))}
					</select>
				</label>

				<span className='map-mode-label'>Geographic view · No statistical values</span>
			</div>

			<div className='map-frame'>
				<div ref={containerRef} className='world-map' role='region' aria-label='Interactive world map' />

				{(!ready || error) && (
					<div className='map-status' role='status'>
						{error || 'Loading world map…'}
					</div>
				)}

				<div className='map-hint'>Drag to explore · Scroll to zoom · Click to select</div>

				{selectedCountry && <CountryPreview country={selectedCountry} onClose={() => setSelectedCountry(null)} />}
			</div>
		</section>
	);
}
