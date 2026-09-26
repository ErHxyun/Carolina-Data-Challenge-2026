import { useEffect, useMemo, useRef, useState } from 'react';
import { Map, NavigationControl, Popup, setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { countryOptions, worldGeometry } from '../../data/worldGeometry';
import { mainCountryPolygon } from '../../data/countryScene';
import { DIMENSIONS, gapColor, mapData, countryResearch } from '../../data/mapResearch';
import { delayText, intervalText, finite } from '../research/format';

setWorkerUrl(workerUrl);
const EMPTY = { type: 'FeatureCollection', features: [] };
const IMAGERY = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

export default function CountrySceneMap() {
	const containerRef = useRef(null);
	const mapRef = useRef(null);
	const homeRef = useRef(null);
	const popupRef = useRef(null);
	const [ready, setReady] = useState(false);
	const [error, setError] = useState('');
	const [notice, setNotice] = useState('');
	const [selectedKey, setSelectedKey] = useState('');
	const [year, setYear] = useState(2021);
	const [dimension, setDimension] = useState('Overall');
	const [atlas, setAtlas] = useState(null);
	const [showColumns, setShowColumns] = useState(true);
	const feature = useMemo(
		() => worldGeometry.features.find((item) => item.properties.mapKey === selectedKey),
		[selectedKey],
	);
	const scene = useMemo(() => {
		if (!feature) return null;
		const ring = mainCountryPolygon(feature)[0];
		return {
			bounds: [
				[Math.min(...ring.map((p) => p[0])), Math.min(...ring.map((p) => p[1]))],
				[Math.max(...ring.map((p) => p[0])), Math.max(...ring.map((p) => p[1]))],
			],
		};
	}, [feature]);
	const mapped = useMemo(() => mapData(worldGeometry, atlas, dimension, year), [atlas, dimension, year]);
	const selected = mapped.features.find((item) => item.properties.mapKey === selectedKey);
	const summary = countryResearch(atlas, feature?.properties.name)?.summary;
	const delay = summary?.delay_2021?.[dimension];
	const progress = summary?.progress_2010_2020?.[dimension];
	useEffect(() => {
		const controller = new AbortController();
		fetch(`${import.meta.env.BASE_URL}data/mia/map_atlas.json`, { signal: controller.signal })
			.then((response) => {
				if (!response.ok) throw new Error('Research map data could not load.');
				return response.json();
			})
			.then(setAtlas)
			.catch((error) => {
				if (error.name !== 'AbortError') setNotice(error.message);
			});
		return () => controller.abort();
	}, []);

	useEffect(() => {
		let map;
		try {
			map = new Map({
				container: containerRef.current,
				center: [0, 20],
				zoom: 1.5,
				minZoom: 0,
				maxZoom: 18,
				maxPitch: 70,
				renderWorldCopies: false,
				style: {
					version: 8,
					sources: {
						imagery: {
							type: 'raster',
							tiles: [IMAGERY],
							tileSize: 256,
							maxzoom: 19,
							attribution: 'Imagery © Esri, Vantor, Earthstar Geographics, GIS User Community',
						},
					},
					layers: [
						{ id: 'background', type: 'background', paint: { 'background-color': '#101012' } },
						{ id: 'imagery', type: 'raster', source: 'imagery' },
					],
				},
				attributionControl: {
					compact: true,
					customAttribution: 'Boundaries: <a href="https://www.naturalearthdata.com/">Natural Earth</a>',
				},
			});
		} catch {
			// Surface an external WebGL initialization failure to the UI.
			// eslint-disable-next-line react-hooks/set-state-in-effect
			setError('The 3D map requires a browser with WebGL2 enabled.');
			return;
		}
		mapRef.current = map;
		map.addControl(new NavigationControl({ visualizePitch: true }), 'top-left');
		map.dragRotate.disable();
		map.touchZoomRotate.disableRotation();
		map.touchPitch.disable();
		const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 12, className: 'country-tooltip' });
		popupRef.current = popup;
		map.on('error', (event) => {
			console.error('Country scene map:', event.error);
			if (event.sourceId === 'imagery')
				setNotice('Satellite imagery is temporarily unavailable. Country geometry remains interactive.');
			else setError(event.error?.message || 'The map could not load.');
		});
		map.on('load', () => {
			map.addSource('countries', { type: 'geojson', data: EMPTY });
			map.addSource('research-extrusion', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'country-hit',
				type: 'fill',
				source: 'countries',
				paint: { 'fill-color': gapColor, 'fill-opacity': ['case', ['get', 'hasData'], 0.65, 0.18] },
			});
			map.addLayer({
				id: 'country-lines',
				type: 'line',
				source: 'countries',
				paint: { 'line-color': '#ffffff', 'line-width': 0.6, 'line-opacity': 0.45 },
			});
			map.addLayer({
				id: 'country-selected',
				type: 'line',
				source: 'countries',
				filter: ['==', ['get', 'mapKey'], ''],
				paint: { 'line-color': '#ffffff', 'line-width': 2.2 },
			});
			map.addLayer({
				id: 'research-columns',
				type: 'fill-extrusion',
				source: 'research-extrusion',
				paint: {
					'fill-extrusion-height': ['get', 'elevation'],
					'fill-extrusion-opacity': 0.94,
					'fill-extrusion-color': gapColor,
					'fill-extrusion-height-transition': { duration: 450 },
				},
			});
			map.on('click', 'country-hit', (event) => {
				if (map.queryRenderedFeatures(event.point, { layers: ['research-columns'] }).length) return;
				popup.remove();
				const key = event.features?.[0]?.properties.mapKey;
				if (key) setSelectedKey(key);
			});
			map.on('mousemove', 'country-hit', (event) => {
				const column = map.queryRenderedFeatures(event.point, { layers: ['research-columns'] })[0];
				const country = event.features?.[0];
				if (!country) return;
				map.getCanvas().style.cursor = 'pointer';
				const p = (column || country).properties;
				const label = `${p.name} · ${p.dimension || 'Overall'} · ${p.year || ''}: ${p.hasData ? Number(p.gap).toFixed(2) + ' relative units (urban − rural)' : 'No estimate available'}`;
				popup.setLngLat(event.lngLat).setText(label).addTo(map);
			});
			map.on('mouseleave', 'country-hit', () => {
				map.getCanvas().style.cursor = '';
				popup.remove();
			});
			const width = containerRef.current.clientWidth;
			map.jumpTo({ center: [0, 20], zoom: Math.max(0, Math.log2(Math.max(width, 512) / 512)) });
			setReady(true);
		});
		const observer = new ResizeObserver(() => {
			if (containerRef.current?.clientWidth && containerRef.current?.clientHeight) map.resize();
		});
		observer.observe(containerRef.current);
		return () => {
			observer.disconnect();
			popup.remove();
			map.remove();
			mapRef.current = null;
			popupRef.current = null;
		};
	}, []);

	useEffect(() => {
		const map = mapRef.current;
		if (!ready || !map) return;
		popupRef.current?.remove();
		map.stop();
		map.setFilter('country-selected', ['==', ['get', 'mapKey'], selectedKey]);
		const duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1100;
		if (scene) {
			if (!homeRef.current) homeRef.current = { center: map.getCenter(), zoom: map.getZoom() };
			map.dragRotate.enable();
			map.touchZoomRotate.enableRotation();
			map.touchPitch.enable();
			const size = map.getContainer();
			const wide = size.clientWidth >= 1000;
			const camera = map.cameraForBounds(scene.bounds, {
				padding: { top: 85, bottom: 105, left: wide ? 280 : 35, right: wide ? 220 : 35 },
				maxZoom: 5,
			});
			if (camera) map.easeTo({ ...camera, zoom: Math.max(0, camera.zoom - 0.25), pitch: 55, bearing: -18, duration });
			map.setPaintProperty('imagery', 'raster-brightness-max', 0.58);
		} else {
			map.dragRotate.disable();
			map.touchZoomRotate.disableRotation();
			map.touchPitch.disable();
			map.getSource('research-extrusion').setData(EMPTY);
			map.easeTo({ ...(homeRef.current || {}), pitch: 0, bearing: 0, padding: 0, duration });
			homeRef.current = null;
			map.setPaintProperty('imagery', 'raster-brightness-max', 1);
		}
	}, [ready, selectedKey, scene]);

	useEffect(() => {
		const map = mapRef.current;
		if (!ready || !map) return;
		popupRef.current?.remove();
		map.getSource('countries').setData(mapped);
		const selected = mapped.features.find((item) => item.properties.mapKey === selectedKey);
		map
			.getSource('research-extrusion')
			.setData(selected?.properties.hasData ? { type: 'FeatureCollection', features: [selected] } : EMPTY);
		map.setLayoutProperty('research-columns', 'visibility', showColumns ? 'visible' : 'none');
	}, [ready, mapped, selectedKey, showColumns]);

	return (
		<section className='map-section' aria-label='World and country data explorer'>
			<div className='map-toolbar'>
				<label className='country-select-label analysis-dimension-control'>
					<span>Explore a country</span>
					<select
						name='scene-country'
						value={selectedKey}
						disabled={!ready}
						onChange={(event) => setSelectedKey(event.target.value)}
					>
						<option value=''>2D world overview</option>
						{countryOptions.map((country) => (
							<option key={country.mapKey} value={country.mapKey}>
								{country.name}
							</option>
						))}
					</select>
				</label>
				<label className='country-select-label analysis-dimension-control'>
					<span>Analysis dimension</span>
					<select name='analysis-dimension' value={dimension} onChange={(event) => setDimension(event.target.value)}>
						{DIMENSIONS.map((d) => (
							<option key={d}>{d}</option>
						))}
					</select>
				</label>
			</div>
			<div className={`map-frame scene-frame${feature ? ' is-country-scene' : ''}`}>
				<div ref={containerRef} className='world-map' role='region' aria-label='Interactive satellite map' />
				{(!ready || error) && (
					<div className='map-status' role='status'>
						{error || 'Loading satellite map…'}
					</div>
				)}
				{notice && !error && (
					<div className='scene-notice' role='status'>
						{notice}
					</div>
				)}
				{feature && (
					<>
						<article className='scene-story'>
							<button type='button' className='scene-back' onClick={() => setSelectedKey('')}>
								← Back to 2D world
							</button>
							<p className='eyebrow'>{dimension} / National analysis</p>
							<h2>{feature.properties.name}</h2>
							<span className='demo-badge'>Bayesian model estimates</span>
							<div className='scene-gap'>
								<span>Urban − rural · {year}</span>
								<strong>{selected?.properties.hasData ? selected.properties.gap.toFixed(2) : 'Unavailable'}</strong>
								<small>Relative opportunity units</small>
							</div>
							<h3>
								Opportunity Delay · 2021
								<br />
								{delayText(delay, summary?.meaningful_gap)}
							</h3>
							<p>
								{summary?.meaningful_gap ? intervalText(delay) : 'No delay ranking without a material overall gap.'}
							</p>
							{finite(delay?.years_to_nearest_obs) && delay.years_to_nearest_obs > 5 && (
								<p>Limited nearby evidence: nearest observation is {delay.years_to_nearest_obs} years from 2021.</p>
							)}
							<h3>{progress?.label || 'No progress classification'}</h3>
							<p>
								Progress classification: 2010–2020. Height shows the absolute national gap; color shows its direction.
								No subnational variation is inferred.
							</p>
							<a
								className='preview-cta'
								href={`#/country/${encodeURIComponent(feature.properties.name)}?dimension=${dimension}`}
							>
								Explore {dimension.toLowerCase()} analysis →
							</a>
						</article>
					</>
				)}
				<aside className='scene-legend' aria-label='Modelled opportunity gap legend'>
					<p className='eyebrow'>{dimension} / Urban − rural</p>
					{[
						['#359db7', '≤ −1.50'],
						['#9cdee8', '−0.25'],
						['#e4e7e9', '0.00'],
						['#ffc278', '+0.25'],
						['#ec7841', '+0.75'],
						['#ad382f', '≥ +1.50'],
						['#555b65', 'No estimate'],
					].map(([color, label]) => (
						<div className='scene-legend-row' key={label}>
							<span style={{ backgroundColor: color }} />
							{label}
						</div>
					))}
					<p>
						Relative model units. Warm = urban higher; cool = rural higher. Color saturates beyond ±1.50. Compare within
						one dimension.
					</p>
					{feature && (
						<>
							<label className='scene-toggle'>
								<input
									type='checkbox'
									checked={showColumns}
									onChange={(event) => setShowColumns(event.target.checked)}
								/>
								Show 3D gap
							</label>
							<p>Height = |gap| × 80 km (display scale, not terrain). Right-drag to rotate.</p>
						</>
					)}
				</aside>
				<div className='scene-timeline'>
					<label htmlFor='scene-year'>
						Model year <strong>{year}</strong>
					</label>
					<input
						id='scene-year'
						type='range'
						min='1990'
						max='2024'
						step='1'
						value={year}
						onChange={(event) => setYear(Number(event.target.value))}
					/>
					<span>National model medians · Delay cards remain at 2021</span>
				</div>
				{!feature && <div className='map-hint'>Color shows opportunity gaps · Click a country for 3D analysis</div>}
			</div>
		</section>
	);
}
