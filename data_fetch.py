import argparse
import csv
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

OUT_ROOT = Path(__file__).resolve().parent / "Graduate_Dataset" / "all_sources"
WORKERS = 4                 # parallel downloads
PER_PAGE = 20000            # rows per request (API accepts large values)
DROP_NULL = True            # drop rows with value == null (most rows are null)
MAX_RETRIES = 4
TIMEOUT = 120


BASE_URL = "https://api.worldbank.org/v2"
_local = threading.local()
_log_lock = threading.Lock()


def session():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
    return _local.s


def get_json(url, params):
    """GET with retry/backoff. Returns parsed JSON (list or dict)."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session().get(url, params=params, timeout=TIMEOUT)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last_err = e
            time.sleep(min(60, 3 * 2 ** (attempt - 1)))
    raise RuntimeError(f"{url} failed after {MAX_RETRIES} tries: {last_err}")


def api_error(payload):
    """Return API error text if payload is an error message, else None."""
    head = payload[0] if isinstance(payload, list) and payload else payload
    if isinstance(head, dict) and "message" in head:
        return str(head["message"])
    return None


def fetch_paginated(url, params):
    params = {**params, "format": "json", "per_page": PER_PAGE, "page": 1}
    rows = []
    while True:
        payload = get_json(url, params)
        err = api_error(payload)
        if err:
            raise ValueError(f"API error: {err}")
        if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
            break
        meta, data = payload[0], payload[1]
        rows.extend(data)
        if params["page"] >= int(meta.get("pages", 1)):
            break
        params["page"] += 1
    return rows


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


def list_sources():
    rows = fetch_paginated(f"{BASE_URL}/sources", {})
    return [r for r in rows if r.get("dataavailability") == "Y"]


def list_indicators(sid):
    rows = fetch_paginated(f"{BASE_URL}/sources/{sid}/indicators", {})
    return [
        {
            "id": r["id"],
            "name": r.get("name"),
            "unit": r.get("unit"),
            "source_org": r.get("sourceOrganization"),
            "topics": "; ".join(t.get("value", "").strip() for t in r.get("topics") or [] if t.get("value")),
            "definition": r.get("sourceNote"),
        }
        for r in rows
    ]

def download_indicator(sid, ind_id, out_dir, date_range, keep_null):
    out_path = out_dir / f"{safe_name(ind_id)}.csv.gz"
    if out_path.exists():
        return ind_id, "skip", None, None

    params = {"source": sid}
    if date_range:
        params["date"] = date_range
    try:
        rows = fetch_paginated(f"{BASE_URL}/country/all/indicator/{ind_id}", params)
    except Exception as e:
        return ind_id, "error", 0, str(e)[:300]

    df = pd.DataFrame(
        {
            "country_id": [(r.get("country") or {}).get("id") for r in rows],
            "country": [(r.get("country") or {}).get("value") for r in rows],
            "iso3": [r.get("countryiso3code") for r in rows],
            "date": [r.get("date") for r in rows],
            "value": [r.get("value") for r in rows],
            "obs_status": [r.get("obs_status") for r in rows],
        }
    )
    if not keep_null:
        df = df.dropna(subset=["value"])

    tmp = out_path.with_suffix(".tmp")
    df.to_csv(tmp, index=False, compression="gzip")
    tmp.replace(out_path)  # atomic: partial files never look finished
    return ind_id, ("ok" if len(df) else "empty"), len(df), None


def append_log(log_path, row):
    with _log_lock:
        new = not log_path.exists()
        with open(log_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["indicator", "status", "rows", "error"])
            w.writerow(row)


def run_source(src, args):
    sid, code, name = src["id"], src.get("code") or "", src["name"].strip()
    out_dir = args.out / f"{int(sid):03d}_{safe_name(code)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog_path = out_dir / "_indicators.csv"
    if catalog_path.exists():
        catalog = pd.read_csv(catalog_path, dtype=str)
    else:
        catalog = pd.DataFrame(list_indicators(sid))
        catalog.to_csv(catalog_path, index=False)

    ids = catalog["id"].tolist() if len(catalog) else []
    todo = [i for i in ids if not (out_dir / f"{safe_name(i)}.csv.gz").exists()]
    print(f"\n[{sid}] {name}: {len(ids)} indicators, {len(todo)} remaining")
    if not todo:
        return

    log_path = out_dir / "_log.csv"
    done, t0 = 0, time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(download_indicator, sid, i, out_dir, args.date, args.keep_null) for i in todo]
        for fut in as_completed(futs):
            ind_id, status, n, err = fut.result()
            if status != "skip":
                append_log(log_path, [ind_id, status, n, err or ""])
            done += 1
            if done % 25 == 0 or done == len(todo):
                rate = done / max(time.time() - t0, 1e-6)
                eta = (len(todo) - done) / rate / 60 if rate else 0
                print(f"  {done}/{len(todo)}  ({rate:.1f}/s, ETA {eta:.0f} min)", flush=True)


# -------------------------------- Main ---------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Download all World Bank API databases.")
    p.add_argument("--list-only", action="store_true", help="inventory only, no data download")
    p.add_argument("--sources", nargs="+", help="only these source ids")
    p.add_argument("--exclude", nargs="+", default=[], help="skip these source ids")
    p.add_argument("--date", default=None, help='e.g. "1990:2025"; default = all years')
    p.add_argument("--workers", type=int, default=WORKERS)
    p.add_argument("--keep-null", action="store_true", default=not DROP_NULL)
    p.add_argument("--out", type=Path, default=OUT_ROOT)
    return p.parse_args()


def main():
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    sources = list_sources()
    if args.sources:
        sources = [s for s in sources if s["id"] in set(args.sources)]
    sources = [s for s in sources if s["id"] not in set(args.exclude)]
    sources.sort(key=lambda s: int(s["id"]))

    if args.list_only:
        summary = []
        for s in sources:
            try:
                n = len(list_indicators(s["id"]))
            except Exception as e:
                n = f"error: {e}"
            summary.append({"id": s["id"], "code": s.get("code"), "name": s["name"].strip(),
                            "lastupdated": s.get("lastupdated"), "n_indicators": n})
            print(f"[{s['id']:>3}] {s['name'].strip()[:55]:<55} {n}")
        df = pd.DataFrame(summary)
        df.to_csv(args.out / "sources.csv", index=False)
        total = pd.to_numeric(df["n_indicators"], errors="coerce").sum()
        print(f"\n{len(df)} sources, {int(total)} indicators total -> {args.out / 'sources.csv'}")
        return

    pd.DataFrame(sources).to_csv(args.out / "sources.csv", index=False)
    for s in sources:
        try:
            run_source(s, args)
        except KeyboardInterrupt:
            print("\nStopped. Re-run the same command to resume.")
            return
        except Exception as e:
            print(f"[{s['id']}] source failed: {e}")
    print("\nAll done. Check each _log.csv for status=error and re-run to retry.")


if __name__ == "__main__":
    main()