# HerTime

**Time. Access. Opportunity.**

HerTime is an interactive research website for exploring how unpaid work, infrastructure access, and opportunity differ across countries and between groups of women. It combines country dashboards with an evidence-based assistant that links local statistical results to retrieved country context.

Developed for the Carolina Data Challenge 2026.

- Frontend: https://erhxyun.github.io/Carolina-Data-Challenge-2026/
- Main development and Pages deployment branch: `main`
- Assistant deployment is separate from GitHub Pages; availability depends on the configured backend and provider accounts.

## What the application includes

- A landing page with historical photographs and entry points to the map or assistant.
- A 2D satellite world map, analysis layers, country selection, and 3D national gap views.
- Country portraits and compact dashboards for opportunity, Time Tax, infrastructure, and education-to-employment conversion.
- Animated chart introductions, observation-year labels, evidence details, and source attribution.
- A conversational Data Assistant with common-question shortcuts, live workflow status, downloadable JSON reports, and two outputs: Research Brief and Policy Roadmap.

## Architecture and technology

| Component | Implementation | Responsibility |
| --- | --- | --- |
| Frontend | React 19, Vite 8, JavaScript, CSS | Navigation, maps, charts, chat |
| Mapping | MapLibre GL JS; satellite imagery and country boundaries | Geographic display and national data layers |
| Analysis | Python notebooks and exported CSV/JSON | Offline data preparation and statistical analysis |
| API | Python `ThreadingHTTPServer` | Routing, HTTP endpoints, NDJSON streaming |
| Orchestration | LangGraph 1.2.12 | Request-scoped graph and parallel agent execution |
| Language models | OpenRouter chat completion API | Interpretation, contextual synthesis, report writing |
| Research retrieval | Tavily Search and Extract | Search results and extracted source text |
| Hosting | GitHub Pages frontend; separately hosted Python backend | Independent frontend/backend deployments |

The current API uses Python's standard-library HTTP server, not FastAPI. Model training is not performed on each chat request.

### Assistant workflow

1. **Understand and locate:** identify a country, topic, optional observation year, and report intent; navigate to the country dashboard.
2. **Statistics and research, in parallel:** load the relevant country records; search and extract complementary context through Tavily.
3. **Write the selected output:** synthesize a Research Brief, or calculate a target scenario and write a Policy Roadmap.

Citation IDs must refer to supplied local evidence or retrieved sources. Failed retrieval or model calls produce a limited report with available evidence rather than invented citations. The system does not prove that a cited source supports every generated sentence; users should inspect the original evidence.

Research normally issues at most two Tavily searches and one extraction request for up to four URLs. OpenRouter and Tavily use the backend owner's credits. Cancelling in the browser does not necessarily stop an already-running provider request.

## Repository layout

```text
.github/workflows/deploy-pages.yml   GitHub Pages build and deployment
Web_Design/
  src/                              React pages, maps, charts, assistant
  public/data/mia/                  Country model exports and dictionary
  public/data/time_tax/             Country Time Tax dashboard exports
  public/data/conversion/           Conversion layers, coverage, provenance
  public/brand/                     Logo and favicon
  public/landing/                   Landing photographs
  scripts/                          Export, import, and data validation tools
Agent_Backend/
  server.py                         HTTP API and agent integration
  workflow.py                       LangGraph orchestration
  policy.py                         Planning intent and target arithmetic
  prompts.py                        Research/statistical/report instructions
  tavily_research.py                 Search and extraction client
  data/                             Four curated runtime analysis exports
  data/manifest.json                 Original paths, sizes, SHA-256 hashes
  test_*.py                         Mocked provider and workflow tests
Analysis_Scripts/                   Offline exploratory notebooks
Graduate_Dataset/                   Local-only source archive (Git-ignored)
data_fetch.py                       Source-data acquisition script
```

## Data policy and reproducibility

**The full `Graduate_Dataset/` directory is intentionally not tracked in the current main branch.** Removing it from the Git index does not delete the maintainer's local files. Earlier commits and other branches may still contain it; this change does not rewrite Git history or purge previous uploads.

A fresh clone can run the website and assistant without that archive:

- Browser-ready datasets remain in `Web_Design/public/data/`.
- Four small analysis exports are stored under `Agent_Backend/data/`: `time_tax_eda/eda.csv.gz`, `infrastructure_friction/infrastructure_friction_analysis.csv.gz`, `time_changes/first_last_changes.csv`, and `freed_time_opportunity/first_last_with_freed_time.csv`.
- `Agent_Backend/data/manifest.json` records the original export paths and file hashes. These are analysis results, not the complete source download.
- Full notebook reproduction requires obtaining the original archive separately and restoring the expected `Graduate_Dataset` layout. A fresh clone is sufficient for application use, not for reproducing every upstream analysis from raw data.
- To use alternative analysis exports, set `HERTIME_ANALYSIS_DATA_DIR` to an absolute directory containing the four expected subfolders. Restart the backend afterward.

Time Tax exports can be refreshed from the selected analysis directory:

```sh
python Web_Design/scripts/export_time_tax.py
```

The conversion exporter requires additional offline inputs; see `Web_Design/README.md`. The Mia importer reads a pinned research-branch snapshot; inspect `scripts/import_mia.py` and fetch that branch before intentionally updating it. Do not regenerate research outputs merely to start the application.

### Meaning and limitations

- Time Tax is national female-minus-male unpaid hours per day. It is distinct from modeled rural-versus-urban opportunity gaps.
- Opportunity trajectories use relative latent units; they are not percentages or directly measured subnational observations.
- Opportunity Delay compares historical trajectories and is labelled with its reference year. It is not a forecast of when equality will occur.
- A 3D country's height encodes a national gap, not terrain, city-level data, or local conditions within the country.
- Latest observations may come from different years. Missing values are not zeros.
- First-to-last comparisons span different intervals; survey comparability is not assumed. Retained quality flags matter.
- Associations, model probabilities, and country residuals do not establish policy effects.
- Policy Roadmap calculations are illustrative target paths. Baseline and target years are separate; old measurements are not presented as current baselines. Unavailable or ambiguous inputs lead to qualitative planning.

## Run locally

Requirements: Python 3.11+ and Node.js 22.12+ in the 22.x release line. Commands below start from the repository root on Windows PowerShell.

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Agent_Backend/requirements.txt
# First setup only: do not overwrite an existing configured .env.
Copy-Item Agent_Backend/.env.example Agent_Backend/.env
.\.venv\Scripts\python.exe Agent_Backend/server.py
```

Before starting the server, fill in `Agent_Backend/.env` using your own credentials. On macOS/Linux, use `.venv/bin/python` instead of the Windows executable path.

### Frontend (second terminal)

```powershell
cd Web_Design
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to `http://127.0.0.1:8001`. The map and static dashboards do not need model keys; the assistant does.

### Environment variables

| Variable | Location | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | Backend only | OpenRouter credential |
| `OPENROUTER_MODEL` | Backend only | Model ID verified in your account |
| `OPENROUTER_ROUTER_MODEL` | Backend, optional | Router override |
| `OPENROUTER_STATISTICAL_MODEL` | Backend, optional | Statistics override |
| `OPENROUTER_RESEARCH_MODEL` | Backend, optional | Context synthesis override |
| `OPENROUTER_REPORT_MODEL` | Backend, optional | Report override |
| `TAVILY_API_KEY` | Backend only | Search and extraction credential |
| `ALLOWED_ORIGINS` | Backend | Comma-separated frontend origins, without path or trailing slash |
| `HERTIME_ANALYSIS_DATA_DIR` | Backend, optional | Alternate analysis-export directory |
| `HOST`, `PORT` | Backend, optional | Bind address and port |
| `VITE_AGENT_API_URL` | Frontend build | Public HTTPS backend origin; not a provider credential |

Never commit `.env` files or expose provider keys through `VITE_*` variables. Example files contain placeholders. Choose an available model supporting the JSON responses expected by this implementation.

## HTTP interface

| Endpoint | Input/output |
| --- | --- |
| `GET /health` | Liveness JSON; does not test external provider credentials |
| `POST /api/route` | Question and optional current country; returns normalized route |
| `POST /api/report` | Validated route; returns report JSON |
| `POST /api/report/stream` | Validated route; emits NDJSON phase events and final report |

Example questions: "Explain time tax changes in Armenia" or "How could Armenia halve its unpaid work gap by 2035?"

## Deploy

### GitHub Pages frontend

1. Use GitHub Actions as the Pages publishing source. If the `github-pages` environment restricts deployment branches, allow `main`.
2. Add repository Actions variable `VITE_AGENT_API_URL` with the deployed backend HTTPS origin.
3. Push frontend changes to `main`, or manually run **Deploy HerTime to GitHub Pages** on `main`.
4. The workflow installs dependencies, runs lint/build, and uploads only `Web_Design/dist`.

The configured Vite build base is `/Carolina-Data-Challenge-2026/`. Change it if hosting under a different repository path or domain root. Hash routes do not need server rewrite rules. Changing `VITE_AGENT_API_URL` requires a new frontend build.

### Render backend

- Connect this repository and set the deployment branch to **main**.
- Leave Root Directory empty: the server also reads files under `Web_Design`.
- Build command: `pip install -r Agent_Backend/requirements.txt`
- Start command: `python Agent_Backend/server.py`
- Health check: `/health`
- Set the backend provider variables and `ALLOWED_ORIGINS=https://erhxyun.github.io`.

Render's `RENDER=true` selects `0.0.0.0`; `PORT` supplies the port. Local defaults remain `127.0.0.1:8001`. Render's branch setting is external to Git and must be updated in its dashboard when migrating from `Eric_Webdesign`.

This backend is a prototype using a standard-library HTTP server. CORS and a three-request semaphore are not authentication, per-user rate limiting, or spending controls. A public deployment needs appropriate gateway/access controls and provider spending limits. Free-instance cold starts can delay the first request.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s Agent_Backend -p "test_*.py"
cd Web_Design
npm run lint
npm run test:data
npm run build
```

Backend tests use mocked providers and local records; passing them does not demonstrate current external-model availability or report quality. Frontend data tests validate conversion exports. `npm run preview` serves the production build under its configured repository path.

## Troubleshooting

- **Backend not connected to this deployment:** configure `VITE_AGENT_API_URL` before rebuilding Pages.
- **Failed to fetch:** check API availability, HTTPS, allowed origin, and cold-start status.
- **No open ports detected:** deploy the updated server with Render's HOST/PORT configuration.
- **Limited evidence:** inspect missing credentials, extraction failures, source coverage, or provider errors. Do not interpret missing results as zero.
- **Missing local records:** verify the runtime exports or the override directory; reinstalling the full source archive is not required for normal application use.

## Attribution

Retain imagery, map, photograph, and data attributions shown in the application. Country exports and conversion provenance files document their sources and limitations. Third-party imagery and photographs retain their respective licenses; repository inclusion does not grant unrestricted reuse.
