"""Bounded Tavily search and extraction. Only extracted pages enter synthesis."""
import json
import os
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


class ResearchUnavailable(RuntimeError):
    pass


def request(endpoint, payload):
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        raise ResearchUnavailable("Tavily is not configured. Set TAVILY_API_KEY in Agent_Backend/.env and restart the backend.")
    req = Request("https://api.tavily.com/" + endpoint,
                  data=json.dumps(payload).encode(),
                  headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def canonical_url(value):
    try:
        parts = urlsplit(value)
        if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
            return None
        return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, parts.query, ""))
    except (ValueError, TypeError):
        return None


def collect_sources(route):
    country = route["country_name"]
    themes = {
        "time_tax": "women unpaid care domestic work childcare employment",
        "time_changes": "women time use survey unpaid care changes childcare employment",
        "freed_time": "women unpaid care childcare labor force participation barriers",
        "infrastructure": "women water electricity clean cooking time burden",
        "opportunity_gap": "women rural urban employment education access inequality",
        "opportunity_delay": "women rural urban development inequality historical progress",
    }
    query = f"{country} {themes.get(route['topic'], themes['opportunity_gap'])} {route.get('year') or ''}".strip()
    queries = [query, f"{country} {route.get('question', '')[:350]} research report"]
    if route.get("output_mode") == "policy_roadmap":
        queries = [f"{country} {themes.get(route['topic'], 'women opportunity')} policy implementation programs",
                   f"{country} {themes.get(route['topic'], 'women opportunity')} policy impact evaluation implementation barriers"]
    candidates, warnings = {}, []
    for i, query in enumerate(queries):
        payload = {"query": query, "search_depth": "advanced", "max_results": 4,
                   "include_answer": False, "include_raw_content": False}
        if i == 0:
            payload["include_domains"] = ["worldbank.org", "ilo.org", "unwomen.org"]
        try:
            data = request("search", payload)
        except ResearchUnavailable:
            raise
        except Exception:
            warnings.append("One Tavily search failed; other returned sources may still be available.")
            continue
        for item in data.get("results", []):
            url = canonical_url(item.get("url"))
            if url and url not in candidates:
                candidates[url] = item
    selected = list(candidates)[:4]
    if not selected:
        return [], warnings + ["No usable search results were returned."]
    try:
        extracted = request("extract", {"urls": selected, "extract_depth": "advanced", "format": "text"})
    except Exception:
        return [], warnings + ["Page extraction failed; search snippets were not treated as full-text evidence."]
    sources = []
    for item in extracted.get("results", []):
        url = canonical_url(item.get("url"))
        content = item.get("raw_content")
        if url not in selected or not isinstance(content, str) or not content.strip():
            continue
        if any(source["url"] == url for source in sources):
            continue
        meta = candidates[url]
        sources.append({"id": f"web-{len(sources)+1}", "url": url,
                        "title": meta.get("title") or url,
                        "excerpt": content[:8000], "published_date": meta.get("published_date"),
                        "retrieval": "tavily_extract", "truncated": len(content) > 8000})
    if len(sources) < len(selected):
        warnings.append("Some pages could not be extracted and were excluded from synthesis.")
    return sources, warnings
