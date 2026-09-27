import { useEffect, useMemo, useRef, useState } from 'react';
import { Map, NavigationControl, Popup, setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { countryOptions, worldGeometry } from '../../data/worldGeometry';
import { mainCountryPolygon } from '../../data/countryScene';
import { DIMENSIONS, GAP_COLORS, gapColor, mapData, countryResearch } from '../../data/mapResearch';
import { delayText, intervalText, finite } from '../research/format';
import {
	VALUE_TYPE_LABEL,
	binOf,
	binsFromStops,
	colorExpression,
	defaultYear,
	formatValue,
	layerBins,
	layerMedian,
	layerYears,
	momentum,
	observationYear,
	spoken,
	supportsExtrusion,
	valueFor,
} from '../../data/conversionScale';
import { conversionMap, isoFor, loadConversionData } from '../../data/conversionResearch';
import ConversionLegend, { LegendRows } from './ConversionLegend';
import LayerPicker from './LayerPicker';
import { conversionTooltip } from './conversionTooltip';
import { RURAL_PREFIX, menuLabel } from '../../data/layerMenu';
import { explainValue, shortValue } from '../../data/layerExplain';

/** What a rural–urban gap value means, without repeating the number shown above it. */
function ruralCaption(gap) {
	if (!finite(gap)) return null;
	if (Math.abs(gap) < 0.05) return 'Rural and urban women are about level on this dimension.';
	return `${gap > 0 ? 'Urban' : 'Rural'} women ahead of ${gap > 0 ? 'rural' : 'urban'} women on the model's opportunity scale.`;
}

setWorkerUrl(workerUrl);
const EMPTY = { type: 'FeatureCollection', features: [] };
const IMAGERY = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
// Legend ranges for the rural–urban gap: the existing colour stops, each owning the values up to
// the midpoint with its neighbours.
const RURAL_BINS = binsFromStops(
	[-1.5, -0.25, 0, 0.25, 0.75, 1.5].map((v, i) => [v, GAP_COLORS[i]]),
	(v) => `${v < 0 ? '\u2212' : v > 0 ? '+' : ''}${Math.abs(v).toFixed(2)}`,
);

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
	const [atlas, setAtlas] = useState(null);
	// One "Analysis dimension" selection covers both the rural–urban dimensions ('rural:<Dimension>')
	// and the conversion layers (layer id). Rural–urban Overall remains the default.
	const [selection, setSelection] = useState(`${RURAL_PREFIX}Overall`);
	const [show3d, setShow3d] = useState(true); // country view only; the world overview is always 2D
	const [legendFilter, setLegendFilter] = useState(null);
	const [conversionWanted, setConversionWanted] = useState(false);
	const [conversion, setConversion] = useState(null);
	const [conversionYear, setConversionYear] = useState(null);
	const tooltipRef = useRef(null);
	const conversionMode = !selection.startsWith(RURAL_PREFIX);
	const dimension = conversionMode ? 'Overall' : selection.slice(RURAL_PREFIX.length);
	const layerId = conversionMode ? selection : null;
	const layer = conversion?.layerById[layerId];
	const shownLayer = useMemo(() => layer && { ...layer, display_label: menuLabel(layer.id, layer.display_label) }, [layer]);
	const layerYearList = layer ? layerYears(conversion, layer) : [];
	const activeYear = conversionYear ?? (layer ? defaultYear(conversion, layer) : null);
    useEffect(() => {
        function navigate(event) {
            const { mapKey, dimension, year } = event.detail;
            if (!countryOptions.some(item => item.mapKey === mapKey)) return;
            setSelectedKey(mapKey);
            if (DIMENSIONS.includes(dimension)) setSelection(`${RURAL_PREFIX}${dimension}`); setLegendFilter(null);
            if (Number.isInteger(year) && year >= 1990 && year <= 2024) setYear(year);
        }
        window.addEventListener('agent:navigate', navigate);
        return () => window.removeEventListener('agent:navigate', navigate);
    }, []);

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
	const bins = useMemo(() => (conversionMode ? (layer ? layerBins(layer) : []) : RURAL_BINS), [conversionMode, layer]);
	const mapped = useMemo(() => {
		const base =
			(conversionMode && conversionMap(worldGeometry, conversion, layerId, activeYear)) ||
			mapData(worldGeometry, conversionMode ? null : atlas, dimension, year);
		// Tag each country with its legend range so a legend click can highlight it.
		return {
			...base,
			features: base.features.map((f) => {
				const p = f.properties;
				const value = !p.hasData ? null : conversionMode ? (p.category ?? p.value) : p.gap;
				return { ...f, properties: { ...p, bin: binOf(bins, value) } };
			}),
		};
	}, [conversionMode, conversion, layerId, activeYear, atlas, dimension, year, bins]);
	const binCounts = useMemo(() => {
		const counts = {};
		for (const f of mapped.features) counts[f.properties.bin] = (counts[f.properties.bin] ?? 0) + 1;
		return counts;
	}, [mapped]);
	const chooseDimension = (id) => {
		setSelection(id);
		setConversionYear(null);
		setLegendFilter(null);
		if (!id.startsWith(RURAL_PREFIX)) setConversionWanted(true);
	};
	const conversionRowSelected = conversionMode && feature ? conversion?.countries[isoFor(feature.properties.name)] : null;
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
		if (!(conversionMode || conversionWanted) || conversion) return;
		let active = true;
		loadConversionData()
			.then((data) => {
				if (active) setConversion(data);
			})
			.catch((error) => {
				if (active) setNotice(error.message);
			});
		return () => {
			active = false;
		};
	}, [conversionMode, conversionWanted, conversion]);

	useEffect(() => {
		tooltipRef.current = conversionMode && shownLayer ? { conversion, layer: shownLayer, year: activeYear } : null;
	}, [conversionMode, conversion, shownLayer, activeYear]);

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
				const context = tooltipRef.current;
				if (context) {
					const node = conversionTooltip(p.name, p.iso || isoFor(p.name), context.conversion, context.layer, context.year);
					popup.setLngLat(event.lngLat).setDOMContent(node).addTo(map);
					return;
				}
				const label = `${p.name} · ${p.dimension || 'Overall'} · ${p.year || ''}: ${p.hasData ? Number(p.gap).toFixed(2) + ' relative units (urban − rural): ' + ruralCaption(Number(p.gap)).toLowerCase() : 'No estimate available'}`;
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
			// 3D tilts the camera and raises the selected country; 2D keeps the same country, flat.
			if (camera)
				map.easeTo({ ...camera, zoom: Math.max(0, camera.zoom - 0.25), pitch: show3d ? 55 : 0, bearing: show3d ? -18 : 0, duration });
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
	}, [ready, selectedKey, scene, show3d]);

	useEffect(() => {
		const map = mapRef.current;
		if (!ready || !map) return;
		popupRef.current?.remove();
		map.getSource('countries').setData(mapped);
		const selected = mapped.features.find((item) => item.properties.mapKey === selectedKey);
		map
			.getSource('research-extrusion')
			.setData(selected?.properties.hasData ? { type: 'FeatureCollection', features: [selected] } : EMPTY);
		const columns = show3d && (conversionMode ? layer && supportsExtrusion(layer) : true);
		map.setLayoutProperty('research-columns', 'visibility', columns ? 'visible' : 'none');
	}, [ready, mapped, selectedKey, show3d, conversionMode, layer]);

	useEffect(() => {
		const map = mapRef.current;
		if (!ready || !map) return;
		// Filtered-out countries are dimmed, not removed, so they stay hoverable and clickable.
		const match = ['==', ['get', 'bin'], legendFilter ?? ''];
		map.setPaintProperty('country-hit', 'fill-opacity', legendFilter ? ['case', match, 0.85, 0.05] : ['case', ['get', 'hasData'], 0.65, 0.18]);
		map.setPaintProperty('country-lines', 'line-opacity', legendFilter ? ['case', match, 0.9, 0.12] : 0.45);
	}, [ready, legendFilter]);

	useEffect(() => {
		const map = mapRef.current;
		if (!ready || !map) return;
		const color = conversionMode && layer ? colorExpression(layer) : gapColor;
		map.setPaintProperty('country-hit', 'fill-color', color);
		map.setPaintProperty('research-columns', 'fill-extrusion-color', color);
	}, [ready, conversionMode, layer]);

	return (
		<section className='map-section' aria-label='World and country data explorer'>
			<div className='map-toolbar'>
				<LayerPicker
					selected={selection}
					layerById={conversion?.layerById}
					onSelect={chooseDimension}
					onOpen={() => setConversionWanted(true)}
				/>
				<label className='country-select-label analysis-dimension-control'>
					<span>Explore a country</span>
					<select
						name='scene-country'
						value={selectedKey}
						disabled={!ready}
						onChange={(event) => setSelectedKey(event.target.value)}
					>
						<option value=''>World overview</option>
						{countryOptions.map((country) => (
							<option key={country.mapKey} value={country.mapKey}>
								{country.name}
							</option>
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
				{feature && conversionMode && (
					<article className='scene-story'>
						<button type='button' className='scene-back' onClick={() => setSelectedKey('')}>
							← Back to 2D world
						</button>
						<p className='eyebrow'>Conversion / National analysis</p>
						<h2>{feature.properties.name}</h2>
						<a className='preview-cta scene-cta' aria-label={`Learn more about ${feature.properties.name}`} href={`#/country/${encodeURIComponent(feature.properties.name)}?topic=conversion`}>
							Learn more →
						</a>
						{shownLayer && <span className='demo-badge'>{VALUE_TYPE_LABEL[shownLayer.value_type]}</span>}
						{shownLayer && <ConversionStoryValue conversion={conversion} layer={shownLayer} row={conversionRowSelected} name={feature.properties.name} year={activeYear} />}
						{!conversionRowSelected && <p>Not in the conversion dataset.</p>}
						{layer && <p>{layer.caveat}</p>}
					</article>
				)}
				{feature && !conversionMode && (
					<>
						<article className='scene-story'>
							<button type='button' className='scene-back' onClick={() => setSelectedKey('')}>
								← Back to 2D world
							</button>
							<p className='eyebrow'>{dimension} / National analysis</p>
							<h2>{feature.properties.name}</h2>
							<a
								className='preview-cta scene-cta'
								aria-label={`Learn more about ${feature.properties.name}`}
								href={`#/country/${encodeURIComponent(feature.properties.name)}?dimension=${dimension}`}
							>
								Learn more →
							</a>
							<span className='demo-badge'>Bayesian model estimates</span>
							<div className='scene-gap'>
								<span>Urban − rural · {year}</span>
								<strong>{selected?.properties.hasData ? selected.properties.gap.toFixed(2) : 'Unavailable'}</strong>
								<small>Relative opportunity units</small>
								{selected?.properties.hasData && <p className='scene-explain'>{ruralCaption(selected.properties.gap)}</p>}
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
						</article>
					</>
				)}
				{feature && (
					<div className='scene-viewmode' role='group' aria-label='Country view'>
						<button type='button' aria-pressed={!show3d} onClick={() => setShow3d(false)}>
							2D
						</button>
						<button type='button' aria-pressed={show3d} onClick={() => setShow3d(true)}>
							3D
						</button>
						<span className='scene-viewmode-divider' aria-hidden='true' />
						{/* Leaving the country is a different action from changing its view, so it sits apart. */}
						<button
							type='button'
							className={`scene-viewmode-world${show3d ? '' : ' is-suggested'}`}
							aria-label='Back to world overview'
							onClick={() => setSelectedKey('')}
						>
							<span aria-hidden='true'>⤢</span> World view
						</button>
					</div>
				)}
				{conversionMode && shownLayer && (
					<ConversionLegend
						layer={shownLayer}
						label={shownLayer.display_label}
						bins={bins}
						filter={legendFilter}
						onFilter={setLegendFilter}
						counts={binCounts}
						total={Object.keys(conversion.countries).length}
					>
						{feature && show3d && supportsExtrusion(shownLayer) && (
							<p>Height = |value| relative to the legend range. Display scale only, not terrain or subnational variation.</p>
						)}
					</ConversionLegend>
				)}
				<aside className='scene-legend' aria-label='Modelled opportunity gap legend' hidden={conversionMode}>
					<p className='eyebrow'>{dimension} / Urban − rural</p>
					<LegendRows bins={RURAL_BINS} filter={conversionMode ? null : legendFilter} onFilter={setLegendFilter} counts={binCounts} />
					<p>
						Relative model units. Warm = urban higher; cool = rural higher. Color saturates beyond ±1.50. Compare within
						one dimension. Click a range to show only those countries.
					</p>
					{feature && show3d && <p>Height = |gap| × 80 km (display scale, not terrain). Right-drag to rotate.</p>}
				</aside>
				{conversionMode && shownLayer && (
					<ConversionTimeControl layer={shownLayer} years={layerYearList} year={activeYear} onChange={setConversionYear} />
				)}
				<div className='scene-timeline' hidden={conversionMode}>
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
				{!feature && (
					<div className='map-hint'>
						{conversionMode
							? 'Color shows the selected layer · Grey = no estimate · Click a country for details'
							: 'Color shows opportunity gaps · Click a country for 3D analysis'}
					</div>
				)}
			</div>
		</section>
	);
}

function ConversionStoryValue({ conversion, layer, row, name, year }) {
	const iso = isoFor(name);
	const value = valueFor(conversion, layer, iso, year);
	const m = layer.id === 'gap_momentum_state' ? momentum(row) : null;
	const obs = observationYear(conversion, layer, iso, year);
	const missing = !m && (value === null || value === undefined);
	const explained = m ? null : explainValue(layer.id, value);
	const median = missing || m ? null : layerMedian(conversion, layer, year);
	const shown = m ? m.state : missing ? '—' : explained?.headline ?? formatValue(layer, value);
	return (
		<div className='scene-gap'>
			<span>
				{layer.display_label}
				{obs ? ` · ${obs}` : ''}
			</span>
			<strong aria-label={missing ? 'No estimate' : spoken(shown)}>{shown}</strong>
			{m && <small>{m.text}</small>}
			{missing && <small>No estimate available{typeof year === 'number' ? ` for ${year}` : ''}</small>}
			{explained && <p className='scene-explain'>{explained.caption}</p>}
			{median && (
				<small className='scene-median'>
					Median across {median.count} economies: {shortValue(layer.id, median.value) ?? formatValue(layer, median.value)}
				</small>
			)}
		</div>
	);
}

function ConversionTimeControl({ layer, years, year, onChange }) {
	if (layer.temporal === 'timeline' && years.length > 1) {
		const count = layer.coverage_by_year?.[year] ?? 0;
		return (
			<div className='scene-timeline'>
				<label htmlFor='conversion-year'>
					{layer.display_label} <strong>{year}</strong>
				</label>
				<input
					id='conversion-year'
					type='range'
					min={years[0]}
					max={years.at(-1)}
					step='1'
					value={year}
					aria-valuetext={`${year}, ${count} economies with a value`}
					onChange={(event) => onChange(Number(event.target.value))}
				/>
				<span>
					{years[0]}–{years.at(-1)} · {count} economies with a value this year · {VALUE_TYPE_LABEL[layer.value_type]}. Missing years stay grey; nothing is interpolated.
				</span>
			</div>
		);
	}
	if (layer.temporal === 'waves') {
		return (
			<div className='scene-timeline'>
				<label htmlFor='conversion-wave'>Survey wave</label>
				<select
					id='conversion-wave'
					className='conversion-wave-select'
					value={String(year)}
					onChange={(event) => onChange(event.target.value === 'latest' ? 'latest' : Number(event.target.value))}
				>
					<option value='latest'>Latest available per country (years differ)</option>
					{years.map((wave) => (
						<option key={wave} value={wave}>
							{wave} wave only
						</option>
					))}
				</select>
				<span>Genuine survey waves only. Countries not surveyed in a wave appear as missing.</span>
			</div>
		);
	}
	return (
		<div className='scene-timeline' role='note'>
			<label>Snapshot layer · no year slider</label>
			<span>{layer.period}. This layer is not an annual series, so no year control is shown.</span>
		</div>
	);
}
