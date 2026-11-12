#!/usr/bin/env python3
"""Scrape NeurIPS proceedings for lab authors and diff against site.json.

NeurIPS papers usually have no DOI and are not deposited in Crossref, so
OpenAlex, Crossref and Semantic Scholar miss them. The proceedings site is
the ground truth for those entries.

Usage:
  python3 scripts/scrape_nips.py                    # 2016-2026, whole lab
  python3 scripts/scrape_nips.py --years 2023-2026
  python3 scripts/scrape_nips.py --author "Erdem Varol"
  python3 scripts/scrape_nips.py --write

By default it only prints a diff. --write saves src/data/nips.json.
"""
import argparse
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://papers.nips.cc"
VIRTUAL = "https://neurips.cc/static/virtual/data/neurips-{year}-orals-posters.json"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "src" / "data" / "site.json"
OUT = ROOT / "src" / "data" / "nips.json"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    for _ in range(2):  # some pages are double-escaped
        s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def index(year):
    """Return (url, book_html, page_html). page_html is None if a fetch is needed.

    Up to 2024 the book page is the full paper list. From 2025 it is a table
    of contents with a link to the main-conference volume.
    """
    base = f"{BASE}/paper_files/paper/{year}"
    try:
        page = fetch(base)
    except Exception:  # noqa: BLE001
        return None, None, None

    m = re.search(r'href="([^"]*main-conference)"[^>]*>[^<]*Main Conference', page)
    if m and len(page) < 500_000:
        return BASE + m.group(1), page, None
    return base, page, page


def parse(page):
    items = []
    # 2022+ uses <li class="conference">; older volumes use <li data-track="...">
    for block in re.findall(r'<li[^>]*data-track="[^"]*"[^>]*>.*?</li>', page, re.S):
        link = re.search(
            r'<a title="paper title"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block, re.S
        )
        authors = re.search(r'<span class="paper-authors">(.*?)</span>', block, re.S)
        track = re.search(r'<span class="paper-track-badge">(.*?)</span>', block, re.S)
        if not link:
            continue
        items.append(
            {
                "title": clean(link.group(2)),
                "authors": clean(authors.group(1)) if authors else "",
                "url": BASE + link.group(1),
                "track": clean(track.group(1)) if track else "",
            }
        )
    return items


def virtual(year):
    """NeurIPS virtual-site JSON, used before the proceedings are published."""
    try:
        data = json.loads(fetch(VIRTUAL.format(year=year)))
    except Exception:  # noqa: BLE001
        return []
    out = []
    for r in data.get("results", []):
        authors = [a.get("fullname", "") for a in r.get("authors", [])]
        out.append(
            {
                "title": clean(r.get("name", "")),
                "authors": clean(", ".join(authors)),
                "url": f"https://neurips.cc/virtual/{year}/poster/{r.get('id')}",
                "track": clean(
                    " / ".join(x for x in (r.get("eventtype"), r.get("session")) if x)
                ),
            }
        )
    return out


def volume(book):
    m = re.search(r"Advances in Neural Information Processing Systems\s+(\d+)", book or "")
    return m.group(1) if m else None


def norm(title):
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()


def lab_names(site):
    """PI + team + alumni from site.json, without parentheticals."""
    names = set()
    pi = (site.get("pi") or {}).get("name", "")
    if pi:
        names.add(re.sub(r"\s*\(.*?\)", "", pi).strip())
    for key in ("team", "alumni"):
        for person in site.get(key, []):
            name = (person.get("name") or "").strip()
            if name:
                names.add(name)
    return sorted(names)


def authored_by(authors, names):
    text = authors.lower()
    return any(name.lower() in text for name in names)


def years_arg(value):
    if "-" in value:
        lo, hi = value.split("-", 1)
        return range(int(lo), int(hi) + 1)
    return [int(y) for y in value.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2016-2026")
    ap.add_argument("--author", help="single author substring (overrides the lab roster)")
    ap.add_argument("--authors", help="comma-separated names (overrides the lab roster)")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    data = json.loads(SITE.read_text(encoding="utf-8"))
    site = data["publications"]
    known = {norm(p["title"]) for p in site}
    names = (
        [a.strip() for a in args.authors.split(",") if a.strip()]
        if args.authors
        else [args.author]
        if args.author
        else lab_names(data)
    )

    found = []
    for year in years_arg(args.years):
        url, book, page = index(year)
        if url:
            if page is None:
                page = fetch(url)
            papers = parse(page)
            vol = volume(book)
            venue = (
                f"Advances in Neural Information Processing Systems {vol}"
                if vol
                else f"NeurIPS {year}"
            )
            source = "proceedings"
        else:
            papers = virtual(year)
            # volumes are numbered consecutively: 2025 = 38, 2026 = 39, ...
            venue = f"Advances in Neural Information Processing Systems {year - 1987}"
            source = "virtual"

        if not papers:
            print(f"{year}: no papers found", file=sys.stderr)
            continue

        hits = [p for p in papers if authored_by(p["authors"], names)]
        for p in hits:
            p["year"] = str(year)
            p["venue"] = venue
        found.extend(hits)
        print(
            f"{year}: {len(hits)} match(es) of {len(papers)} papers ({source})",
            file=sys.stderr,
        )

    found = sorted(
        {p["url"]: p for p in found}.values(),
        key=lambda p: (-int(p["year"]), p["title"]),
    )

    print(json.dumps(found, ensure_ascii=False, indent=2))

    print("\n--- diff vs site.json ---", file=sys.stderr)
    for p in found:
        mark = "present" if norm(p["title"]) in known else "NEW"
        print(f"{mark:7} {p['year']}  {p['title']}", file=sys.stderr)

    if args.write:
        OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
