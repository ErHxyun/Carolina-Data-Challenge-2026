# GlobalStat

React/Vite national opportunity explorer with satellite maps, 2D/3D national gap layers, country portraits and animated research charts.

## Local development

Use Node.js 22.12 or newer in the 22.x release line.

```sh
cd Web_Design
npm ci
npm run dev
```

## Checks and production preview

```sh
npm run lint
npm run build
npm run preview
```

Production assets use `/Carolina-Data-Challenge-2026/`. Open that path on the preview server. Hash-based country routes support direct links without a server rewrite.

## GitHub Pages

The root `.github/workflows/deploy-pages.yml` builds and deploys pushes to `Eric_Webdesign`. It uploads only `Web_Design/dist`, not notebooks or raw datasets.

One-time repository setup: Settings > Pages > Build and deployment > Source > GitHub Actions. If the `github-pages` environment restricts branches, allow `Eric_Webdesign`. Re-run a failed deployment after changing settings.

Expected site: https://erhxyun.github.io/Carolina-Data-Challenge-2026/

## Research data

`public/data/mia` contains the pinned research exports with provenance and a data dictionary. `scripts/import_mia.py` refreshes exports from local `origin/Mia_womengap` and rebuilds the atlas; fetch that branch first when intentionally updating the research snapshot. `scripts/build_map_atlas.py` can rebuild just the atlas from existing country exports.

Map colors show urban-minus-rural model medians; 3D height represents the absolute national gap, not subnational observations or terrain. Delay estimates remain labelled 2021. Missing values are not zeros. Time Tax and the AI assistant are not connected yet.

Satellite imagery and country photographs require external services; on-screen attribution and license details are retained.

## Education-to-employment conversion view

The map's "Analysis dimension" button opens a card picker with two tabs: **Over time** (annual series with a year slider) and **Latest snapshot** (no slider). The existing rural–urban dimensions are the default ("Over time → Rural vs urban women"); the new cards ask why women's educational progress translates into employment opportunity in some countries but stalls in others. Legend ranges are clickable filters (other countries are dimmed, not removed). Selecting a country opens it in 3D by default; a 2D | 3D control keeps the same country while flattening or tilting the view. The world overview is always 2D.

**Data.** `public/data/conversion/` holds pinned, browser-ready JSON: `snapshot_atlas.json` (latest values by ISO3), `timeline_atlas.json` (`values[ISO3][i]` for `years[i]`; `null` = no observation), `layers.json` (layer registry), `coverage.json`, `evidence_reports.json` (six reviewed reports) and `provenance.json` (inputs, SHA-256 hashes, counts, validation results). Countries join through the existing `src/data/researchCountryCodes.json`.

**Rebuild** (offline; needs the conversion package and the raw `Graduate_Dataset/all_sources` archive @ f234e5f):

```sh
python3 scripts/build_conversion_web_data.py --package <womens-opportunity-conversion-map> --sources <graduate_all_sources>
python3 scripts/audit_source_coverage.py --sources <graduate_all_sources> --package <womens-opportunity-conversion-map> --out <audit dir>
npm run test:data
```

**Layers.** Main story: education ahead of employment, opportunity conversion surprise, education progress without employment progress, gap momentum (always with its three state probabilities), sticky-gap risk, data visibility. Over time (year slider limited to each layer's real range): education gap, employment gap, conversion gap, women's labour-force participation, women's vulnerable employment, rural electricity gap, rural clean-cooking gap. More lenses (snapshots; Findex and ID shown by genuine survey wave): financial inclusion gap, digital access gap, women's ID ownership, unpaid-care time tax, maternal mortality (log scale), rural time-tax infrastructure gap, widening probability, halving probability, asynchronous data years, data-invisibility metrics.

**Methodology.** Residuals are investigation triggers, not causal effects. Momentum states and first-passage values are model probabilities, not forecasts or promises. Education and employment indicators can refer to different cohorts and years. High participation can include vulnerable, informal or unpaid work. ILO labour series are modelled estimates and are labelled as such; observed series keep their gaps. Missing data are not zero, and nothing is interpolated. Evidence reports contextualize signals and are not causal attribution.

**Checks.** `npm run lint`, `npm run test:data` and `npm run build`.
