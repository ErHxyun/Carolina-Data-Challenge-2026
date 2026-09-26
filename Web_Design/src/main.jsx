import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import 'maplibre-gl/dist/maplibre-gl.css';
import 'leaflet/dist/leaflet.css';

import './styles/global.css';
import './styles/map.css';
import './styles/country.css';
import './styles/leaflet-map.css';
import './styles/country-scene.css';

import App from './App';

createRoot(document.getElementById('root')).render(
	<StrictMode>
		<App />
	</StrictMode>,
);
