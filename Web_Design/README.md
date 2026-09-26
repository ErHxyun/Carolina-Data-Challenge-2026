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
