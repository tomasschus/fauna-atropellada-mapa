"""Paginate the Epicollect5 API for the 'Red Argentina de Monitoreo de Fauna
Atropellada' project and dump every entry to ./epicollect/all_entries.json.
"""
import json, time, os, sys, urllib.request, urllib.error
from urllib.parse import urlencode

BASE = ("https://five.epicollect.net/api/internal/entries/"
        "red-argentina-de-monitoreo-de-fauna-atropellada")

PARAMS = {
    "form_ref": "c8e2f576c4d244cd9b3dad90400cb988_596e95c4d2fdb",
    "per_page": "50",
    "sort_by": "created_at",
    "sort_order": "DESC",
    "map_index": "1",
    "format": "json",
    "headers": "true",
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "epicollect")
os.makedirs(OUT_DIR, exist_ok=True)
ALL_OUT = os.path.join(OUT_DIR, "all_entries.json")

def build_url(page):
    q = dict(PARAMS, page=str(page))
    return f"{BASE}?{urlencode(q)}"

def fetch(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (data-extract)",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            wait = 2 ** attempt
            print(f"  error {e}; retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"failed: {url}")

def main():
    all_entries = []
    page = 1
    total_pages = None
    while True:
        data = fetch(build_url(page))
        with open(os.path.join(OUT_DIR, f"page_{page:04d}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        meta = data.get("meta", {}) or {}
        d = data.get("data", {})
        entries = d.get("entries", []) if isinstance(d, dict) else (d or [])
        if total_pages is None:
            total_pages = meta.get("last_page")
            print(f"meta: total={meta.get('total')} per_page={meta.get('per_page')} last_page={total_pages}")
        print(f"page {page}: {len(entries)} entries (running {len(all_entries)+len(entries)})")
        all_entries.extend(entries)
        if not entries or (total_pages and page >= int(total_pages)):
            break
        page += 1
        time.sleep(0.3)
    with open(ALL_OUT, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False)
    print(f"done: {len(all_entries)} entries -> {ALL_OUT}")

if __name__ == "__main__":
    main()
