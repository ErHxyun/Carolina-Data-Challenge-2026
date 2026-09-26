# App

`legacy_stage_map.html` is the previous self-contained map prototype. It visualizes descriptive stages and desynchronization using embedded SVG geometry and data.

It is retained as a design and interaction reference, not as the final analytical interface. The next version should:

- load `../data/map/country_map_layers.csv` or `map_layers_long.csv`;
- read metadata from `layer_catalog.json`;
- join by `iso3`;
- support the recommended continuous and probability layers;
- use `country_detail_cards.json` for the side panel;
- preserve missingness and show coverage;
- avoid arbitrary threshold-based stage labels as the primary view.
