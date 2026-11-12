#!/usr/bin/env python3
"""Minimal SerpApi CLI.

  python3 scripts/serp.py google_scholar_author author_id=7GlElV0AAAAJ num=100
  python3 scripts/serp.py google_scholar_author author_id=... --out scholar.json

Reads SERPAPI_KEY from the environment or .env. Anything after the engine is a
key=value query parameter, so this works for any SerpApi engine.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = "https://serpapi.com/search"


def api_key():
    key = os.environ.get("SERPAPI_KEY")
    if key:
        return key.strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("SERPAPI_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("SERPAPI_KEY not set (put it in .env or export it)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", help="e.g. google_scholar_author")
    ap.add_argument("params", nargs="*", help="key=value pairs")
    ap.add_argument("--out", help="write JSON here instead of stdout")
    ap.add_argument("--no-cache", action="store_true", help="bypass the 1h cache")
    ap.add_argument("--keys", help="comma-separated top-level keys to print")
    args = ap.parse_args()

    params = {"engine": args.engine, "api_key": api_key()}
    for item in args.params:
        if "=" not in item:
            ap.error(f"expected key=value, got {item!r}")
        k, v = item.split("=", 1)
        params[k] = v
    if args.no_cache:
        params["no_cache"] = "true"

    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "neuroinformaticslab-site/1.0"}
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)

    if args.keys:
        data = {k: data.get(k) for k in args.keys.split(",")}

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
