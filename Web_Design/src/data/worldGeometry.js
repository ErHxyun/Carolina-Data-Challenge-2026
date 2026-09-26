import countries from './countries.geo.json';

export const worldGeometry = {
	type: 'FeatureCollection',
	features: countries.features
		.filter((country) => country.properties.ADMIN !== 'Antarctica')
		.map((country, index) => ({
			type: 'Feature',
			id: index,
			geometry: country.geometry,
			properties: {
				name: country.properties.ADMIN,
                region: country.properties.SUBREGION || country.properties.CONTINENT,
				mapKey: String(index),
			},
		})),
};

export const countryOptions = worldGeometry.features
	.map(({ properties }) => ({
		mapKey: properties.mapKey,
		name: properties.name,
        region: properties.region,
	}))
	.sort((a, b) => a.name.localeCompare(b.name));
