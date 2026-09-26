import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';

import { countryOptions, worldGeometry } from '../../data/worldGeometry';
import CountryPreview from './CountryPreview.jsx';

const defaultStyle = {
	color: '#e0e7ed',
	weight: 0.7,
	opacity: 0.4,
	fillColor: '#ffffff',
	fillOpacity: 0,
};

const selectedStyle = {
	color: '#ffffff',
	weight: 2.5,
	opacity: 1,
	fillOpacity: 0,
};

function getCountryFocusBounds(feature) {
	const geometry = feature.geometry;

	if (geometry.type !== 'MultiPolygon') {
		return L.geoJSON(feature).getBounds();
	}

	function approximateArea(polygon) {
		const ring = polygon[0];
		let area = 0;

		for (let i = 0; i < ring.length - 1; i += 1) {
			const [x1, y1] = ring[i];
			const [x2, y2] = ring[i + 1];
			area += x1 * y2 - x2 * y1;
		}

		const averageLatitude = ring.reduce((sum, coordinate) => sum + coordinate[1], 0) / ring.length;

		return Math.abs(area) * Math.cos((averageLatitude * Math.PI) / 180);
	}

	const mainPolygon = geometry.coordinates.reduce((largest, polygon) =>
		approximateArea(polygon) > approximateArea(largest) ? polygon : largest,
	);

	return L.geoJSON({
		type: 'Feature',
		properties: {},
		geometry: {
			type: 'Polygon',
			coordinates: mainPolygon,
		},
	}).getBounds();
}

export default function LeafletWorldMap() {
	const containerRef = useRef(null);
	const countriesRef = useRef(null);
	const mapRef = useRef(null);

	const [selectedCountry, setSelectedCountry] = useState(null);
	const [tileError, setTileError] = useState(false);

	useEffect(() => {
		const map = L.map(containerRef.current, {
			center: [20, 0],
			zoom: 2,
			minZoom: 0,
			maxZoom: 19,

			// Allow an exact zoom level calculated from the panel dimensions.
			zoomSnap: 0,
			zoomDelta: 0.5,

			maxBounds: [
				[-85.05112878, -180],
				[85.05112878, 180],
			],
			maxBoundsViscosity: 1,

			scrollWheelZoom: true,
			attributionControl: true,
		});

		mapRef.current = map;

		// Match map.html: satellite imagery with detailed road and place overlays.
		const tileOptions = {
			maxZoom: 19,
			maxNativeZoom: 19,
			noWrap: true,
			bounds: [
				[-85.05112878, -180],
				[85.05112878, 180],
			],
			referrerPolicy: 'strict-origin-when-cross-origin',
		};

		const tiles = L.tileLayer(
			'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
			{
				...tileOptions,
				minZoom: 0,
				attribution:
					'Imagery &copy; <a href="https://www.esri.com/">Esri</a>, Vantor, Earthstar Geographics, and the GIS User Community',
			},
		);

		tiles.on('tileerror', () => setTileError(true));
		tiles.addTo(map);

		const referenceCredit =
			'Labels: Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, and the GIS User Community';

		L.tileLayer(
			'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}',
			{ ...tileOptions, minZoom: 13, opacity: 0.9, attribution: referenceCredit },
		).addTo(map);

		L.tileLayer(
			'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
			{ ...tileOptions, minZoom: 13, attribution: referenceCredit },
		).addTo(map);

		const countries = L.geoJSON(worldGeometry, {
			style: defaultStyle,

			onEachFeature(feature, layer) {
				const { name, mapKey } = feature.properties;

				const label = document.createElement('span');
				label.textContent = name;

				layer.bindTooltip(label, {
					sticky: true,
					direction: 'top',
					className: 'leaflet-country-tooltip',
				});

				layer.on('click', () => {
					layer.closeTooltip();
					setSelectedCountry({ name, mapKey });
				});
			},
		}).addTo(map);

		countriesRef.current = countries;

		map.attributionControl.addAttribution('Boundaries: <a href="https://www.naturalearthdata.com/">Natural Earth</a>');

		let initialized = false;

		const resizeObserver = new ResizeObserver(() => {
			const container = containerRef.current;

			if (!container?.clientWidth || !container?.clientHeight) return;

			map.invalidateSize({
				pan: false,
				animate: false,
			});

			const { x: width, y: height } = map.getSize();

			// At zoom 0, the standard tile world is 256 pixels wide.
			// Scale it to cover the panel, with a small margin at the edges.
			const coverZoom = Math.log2((Math.max(width, height) * 1.02) / 256);

			// Prevent zooming out far enough to expose empty side margins.
			map.setMinZoom(coverZoom);

			if (!initialized) {
				map.setView([20, 0], coverZoom, {
					animate: false,
				});

				initialized = true;
			}
		});

		resizeObserver.observe(containerRef.current);

		return () => {
			resizeObserver.disconnect();
			countriesRef.current = null;
			mapRef.current = null;
			map.remove();
		};
	}, []);

	useEffect(() => {
		const countries = countriesRef.current;
		const map = mapRef.current;
		if (!countries || !map) return;

		let selectedLayer = null;

		countries.eachLayer((layer) => {
			const isSelected = layer.feature.properties.mapKey === selectedCountry?.mapKey;
			layer.setStyle(isSelected ? selectedStyle : defaultStyle);

			if (isSelected) {
				layer.bringToFront();
				selectedLayer = layer;
			}
		});

		map.stop();
		if (!selectedLayer) return;

		const bounds = getCountryFocusBounds(selectedLayer.feature);
		if (!bounds.isValid()) return;

		const isWide = map.getSize().x >= 900;
		const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

		// Frame the main landmass while keeping every territory outlined.
		map.flyToBounds(bounds, {
			paddingTopLeft: [40, 40],
			paddingBottomRight: isWide ? [390, 60] : [40, 60],
			maxZoom: Math.max(7, map.getMinZoom()),
			duration: 0.9,
			animate: !reduceMotion,
		});
	}, [selectedCountry]);

	function handleCountryChange(event) {
		const country = countryOptions.find((item) => item.mapKey === event.target.value);

		setSelectedCountry(country ?? null);
	}

	return (
		<section className='map-section' aria-label='Explore countries'>
			<div className='map-toolbar'>
				<label className='country-select-label'>
					<span>Explore a country</span>

					<select value={selectedCountry?.mapKey ?? ''} onChange={handleCountryChange}>
						<option value=''>Select a country</option>

						{countryOptions.map((country) => (
							<option key={country.mapKey} value={country.mapKey}>
								{country.name}
							</option>
						))}
					</select>
				</label>

				<span className='map-mode-label'>Satellite view · Analysis placeholders</span>
			</div>

			<div className='map-frame leaflet-frame'>
				<div ref={containerRef} className='world-map leaflet-canvas' role='region' aria-label='Interactive world map' />

				{tileError && (
					<div className='leaflet-tile-notice' role='status'>
						Some basemap tiles could not load. Country selection remains available.
					</div>
				)}

				<div className='map-hint'>Drag to explore · Scroll to zoom · Click to select</div>

				{selectedCountry && <CountryPreview country={selectedCountry} onClose={() => setSelectedCountry(null)} />}
			</div>
		</section>
	);
}
