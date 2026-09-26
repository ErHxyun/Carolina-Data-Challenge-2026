// Synthetic spatial cells for UI demonstration only; never research observations.
export function pointInRing([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export function pointInPolygon(point, polygon) {
  return pointInRing(point, polygon[0]) && !polygon.slice(1).some((ring) => pointInRing(point, ring));
}

function area(polygon) {
  const ring = polygon[0];
  let sum = 0;
  for (let i = 1; i < ring.length; i++) sum += ring[i - 1][0] * ring[i][1] - ring[i][0] * ring[i - 1][1];
  const latitude = ring.reduce((total, point) => total + point[1], 0) / ring.length;
  return Math.abs(sum) * Math.cos(latitude * Math.PI / 180);
}

export function mainCountryPolygon(feature) {
  const polygons = feature.geometry.type === 'MultiPolygon' ? feature.geometry.coordinates : [feature.geometry.coordinates];
  return polygons.reduce((largest, polygon) => area(polygon) > area(largest) ? polygon : largest);
}

export function buildCountryScene(feature) {
  const polygon = mainCountryPolygon(feature);
  const xs = polygon[0].map((point) => point[0]);
  const ys = polygon[0].map((point) => point[1]);
  const west = Math.min(...xs), east = Math.max(...xs);
  const south = Math.min(...ys), north = Math.max(...ys);
  const width = east - west, height = north - south;
  const dx = width / 30, dy = height / 30;
  const features = [];
  const seed = [...feature.properties.name].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const heightScale = Math.max(width * Math.cos((south + north) * Math.PI / 360), height) * 111000 * 0.08;

  for (let row = 0; row < 30; row++) {
    for (let col = 0; col < 30; col++) {
      const x = west + (col + 0.5) * dx, y = south + (row + 0.5) * dy;
      const ring = [[x-dx*0.23,y-dy*0.23],[x+dx*0.23,y-dy*0.23],[x+dx*0.23,y+dy*0.23],[x-dx*0.23,y+dy*0.23],[x-dx*0.23,y-dy*0.23]];
      if (!pointInPolygon([x,y], polygon) || !ring.every((point) => pointInPolygon(point, polygon))) continue;
      const base = 12 + ((row * 73 + col * 37 + seed) % 80);
      features.push({ type: 'Feature', properties: { cell: `Grid ${row + 1}-${col + 1}`, base, phase: (row+col)%7, heightScale }, geometry: { type: 'Polygon', coordinates: [ring] } });
    }
  }
  return { bounds: [[west,south],[east,north]], cells: { type: 'FeatureCollection', features } };
}

export function sceneForYear(scene, year) {
  return {
    type: 'FeatureCollection',
    features: scene.cells.features.map((feature) => {
      const { base, phase, heightScale } = feature.properties;
      const value = Math.round(Math.max(1, Math.min(100, base + 14 * Math.sin((year - 2010) * 0.45 + phase))));
      return { ...feature, properties: { ...feature.properties, value, year, elevation: heightScale * value / 100 } };
    }),
  };
}
