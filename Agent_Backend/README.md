# GlobalStat assistant — local prototype

Three layers: Query & Navigation → Statistical + Research agents in parallel → Report agent.
The browser uses the same map selection state as manual interaction, then opens the country profile.
The model provider is OpenRouter. No key is shipped to the browser.

## Run locally (PowerShell, repository root)

1. Copy the template once: `Copy-Item Agent_Backend/.env.example Agent_Backend/.env`.
2. Edit Agent_Backend/.env in your editor: set OPENROUTER_API_KEY and OPENROUTER_MODEL to a model ID available in your OpenRouter account.
   Optional per-role model variables override the shared model. Select a model supporting JSON responses for router/statistical/report.
3. Install dependencies: `python -m pip install -r Agent_Backend/requirements.txt`, then run `python Agent_Backend/server.py` (Python 3.11+).
4. In another terminal: `cd Web_Design`, then `npm run dev -- --port 5173 --strictPort`.
5. Ask “Explain time tax changes over time in Armenia” or “Employment opportunity delay in China in 2021”.

The assistant is available on both the world map and country page. It supports one country and an optional single year per request.
Statistical and Research agents run concurrently. A failed web call leaves the statistical evidence available.
The current prompt is retained for report generation; previous conversations are not stored. “This country” can use the open profile.
Stop cancels browser requests and navigation, but an already-running provider call may still finish and incur cost.
Model text is shown as text, not executable HTML. Citation links come only from Tavily search results with successfully extracted content.
Reports can be downloaded as JSON with the complete data bundle and source list.

## Data and meaning

- Opportunity gap/delay: Web_Design/public/data/mia/{ISO}.json. Delay is fixed to 2021; other years do not borrow it.
- National time tax: time_tax_eda/eda.csv.gz.
- Infrastructure friction: infrastructure_friction/infrastructure_friction_analysis.csv.gz.
- Time change: time_changes/first_last_changes.csv.
- Freed time: freed_time_opportunity/first_last_with_freed_time.csv.

Paths above are relative to Agent_Backend/data unless otherwise stated. These four curated exports retain their original Graduate_Dataset provenance in data/manifest.json. Set HERTIME_ANALYSIS_DATA_DIR to use another export directory. The full Graduate_Dataset directory is local-only and ignored.
First-to-last tables filter requested years on their endpoint. They do not implement arbitrary date-range analysis.
Country-specific pooled correlations are not recalculated by this version.
Existing flags, missing values, model uncertainty and subgroup definitions remain in the evidence.
National time-use observations are distinct from rural/urban opportunity estimates.

Regenerate the static time-use dashboard bundle after updating analysis exports:
`python Web_Design/scripts/export_time_tax.py`

## Validation

`python -m unittest discover -s Agent_Backend -v`
`cd Web_Design; npm run lint; npm run build`

Tests mock provider calls; live OpenRouter model compatibility, search availability and response quality require a configured account.
Schema and citation-ID checks do not prove semantic support for every generated sentence.
Read model synthesis alongside its raw records and original sources.

## GitHub Pages and backend hosting

GitHub Pages hosts only the static frontend. Production builds have no backend URL by default and explicitly say the assistant is not connected.
Set VITE_AGENT_API_URL to your HTTPS backend origin **at build time**; never set a VITE_OPENROUTER_API_KEY.
Agent_Backend/.env and Web_Design/.env.local are ignored by Git.

The server defaults to 127.0.0.1:8001 locally. On Render (RENDER=true), it binds to 0.0.0.0 and reads PORT. HOST can explicitly override the bind address. GET /health is a lightweight liveness check, not a provider-key test.
For public hosting, use an authenticated, rate-limited HTTPS gateway and configure ALLOWED_ORIGINS.
CORS and a concurrency limit are not user authentication or a spending quota.
Do not expose this server directly to the internet. Deployment of that gateway is a separate step.

OpenRouter API: https://openrouter.ai/api/v1/chat/completions
Research uses Tavily Search + Extract directly over HTTPS; OpenRouter only synthesizes the retrieved evidence. Set TAVILY_API_KEY in Agent_Backend/.env and restart the backend. Each question uses at most two advanced searches and one extraction request for at most four URLs. Failed extraction excludes that page. No automatic fallback to OpenRouter search is performed. These calls use your Tavily credits.

Missing keys or failed retrieval return a limited research phase while retaining local statistics. Extracted excerpts (up to 8000 characters per source), source IDs, and available publication dates are preserved in report JSON. Citation-ID validation does not prove factual support.

Tavily documentation: https://docs.tavily.com/documentation/api-reference/endpoint/search

## Report writing

Prompts are maintained in prompts.py (research-brief-v2). Reports lead with an answer, explain the data, connect relevant country context, and end with one useful follow-up question. The original question is passed explicitly to the report writer. Context search favors complementary explanations over repeated metrics. Prompt changes take effect after restarting the backend. The JSON report format remains compatible with the existing UI.

## LangGraph orchestration

`workflow.py` defines typed, request-scoped state and two compiled graphs:
- `/api/route`: START -> router -> END. Returns navigation immediately.
- `/api/report` and `/api/report/stream`: START -> prepare -> [statistics || research] -> report -> END.

The report node has an explicit join on both analysis branches. Each branch writes its own state key. Custom LangGraph events become the existing NDJSON phase messages on a single HTTP writer thread. The final JSON schema, OpenRouter calls, prompts, citation validation, and service-unavailable fallbacks are unchanged.

This version does not configure a checkpointer, persistent conversation memory, LangSmith tracing, or automatic paid-call retries. Each request starts with isolated state. Provider calls remain mocked in automated tests.

## Output branches

Statistics and web research join before routing to Research Brief or Policy Roadmap. The roadmap computes an illustrative target from historical data and an explicit target year/reduction; it is not a policy-effect forecast. Streaming events use `report` or `roadmap` for the final stage. See the root README for deployment and reproduction instructions.
