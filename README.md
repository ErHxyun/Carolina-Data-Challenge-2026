# Conversion view — how to apply

Adds the education-to-employment conversion view to GlobalStat (map card picker, clickable legend,
2D | 3D | World view control, Conversion dashboard, real Time Tax data). The rural–urban view stays
the default and `public/data/mia` is untouched.

Based on `Eric_Webdesign` @ 581bc54. From the repo root:

```sh
git checkout -b gloria-conversion-integration Eric_Webdesign
git am conversion-view.patch
cd Web_Design && npm ci && npm run lint && npm run test:data && npm run build && npm run dev
```

Existing files I touched (please check): `CountrySceneMap.jsx` (dimension dropdown → card picker; legend
labels are now clickable ranges; "Show 3D gap" checkbox → 2D/3D/World control), `ResearchPanel.jsx` and
`ComparisonChart.jsx` (small captions moved into the "Sources, methods & coverage" / "View data table"
details), `CountryPage.jsx` (Conversion tab, "Back to world map" button, topic intro line hidden), plus
one line each in `App.jsx`, `mockData.js`, `main.jsx`, `package.json`. No new dependencies.
