#!/usr/bin/env python3
"""Build a reviewable publications diff from Crossref, OpenAlex, SerpApi, and NeurIPS.

Decision record (2026-11-12):
  * Strategy B: fetch, normalize, match, and write a review diff.
  * Approval: GitHub PR; nothing is auto-merged.
  - Preprint policy 1: keep a preprint until a published version exists, then
    replace the preprint row with the published version.
  - Venue display: short label plus year (rendered in src/pages/index.astro).
  * NeurIPS 2026: merge the first two papers; exclude the third by title.

Usage:
  python3 scripts/sync_publications.py              # dry run, writes review files
  python3 scripts/sync_publications.py --apply      # apply an approved review
  python3 scripts/sync_publications.py --offline    # skip network adapters
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "src" / "data" / "site.json"
DOIS = ROOT / "src" / "data" / "dois.json"
NIPS = ROOT / "src" / "data" / "nips.json"
CONFIG = ROOT / "src" / "data" / "publications.config.json"
REVIEW_DIR = ROOT / "publications-review"
REVIEW = REVIEW_DIR / "review.json"
DIFF = REVIEW_DIR / "diff.md"
PR_BODY = REVIEW_DIR / "pr-body.md"
UA = "neuroinformaticslab-site/1.0 (mailto:ev2240@nyu.edu)"
PREPRINT_MARKERS = ("biorxiv", "medrxiv", "arxiv", "research square", "ssrn")
DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "https://dx.doi.org/")
BAD_TITLE_PREFIXES = (
    "author response",
    "correction",
    "erratum",
    "retraction",
    "comment on",
    "editorial",
    "peer review",
)
BAD_TYPES = {"peer-review", "paratext", "editorial", "letter", "erratum", "retraction"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def clean_text(value) -> str:
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


def norm_title(value: str) -> str:
    value = clean_text(value).lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def norm_doi(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    for prefix in DOI_PREFIXES:
        if value.startswith(prefix):
            return value[len(prefix):]
    return value.removeprefix("doi:").strip()


def is_preprint(entry: dict) -> bool:
    venue = (entry.get("venue") or "").lower()
    doi = norm_doi(entry.get("doi"))
    return (
        any(marker in venue for marker in PREPRINT_MARKERS)
        or doi.startswith("10.1101/")
        or doi.startswith("10.21203/")
        or doi.startswith("10.48550/arxiv.")
        or entry.get("type") == "preprint"
    )


def entry_link(entry: dict, dois: dict) -> str | None:
    if entry.get("url"):
        return entry["url"]
    doi = norm_doi(entry.get("doi")) or norm_doi(
        (dois.get(norm_title(entry.get("title", ""))) or {}).get("doi")
    )
    if not doi or doi.startswith("10.52202/"):
        return None
    return f"https://doi.org/{doi}"


def http_json(url: str, timeout: int = 60):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def get_serp_key() -> str:
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if key:
        return key
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("SERPAPI_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def crossref_search(title: str) -> dict | None:
    query = urllib.parse.quote(title)
    url = (
        "https://api.crossref.org/works?"
        f"query.bibliographic={query}&rows=5"
        "&select=DOI,title,author,container-title,issued,type,URL"
        "&mailto=ev2240@nyu.edu"
    )
    try:
        data = http_json(url)
    except Exception as exc:  # noqa: BLE001
        print(f"  Crossref failed: {exc}", file=sys.stderr)
        return None

    wanted = norm_title(title)
    for item in data.get("message", {}).get("items", []):
        titles = item.get("title") or []
        if not titles:
            continue
        found_title = clean_text(titles[0])
        if norm_title(found_title) != wanted:
            continue
        authors = []
        for author in item.get("author") or []:
            name = " ".join(
                part for part in (author.get("given"), author.get("family")) if part
            ).strip()
            if name:
                authors.append(name)
        year = ""
        parts = (item.get("issued") or {}).get("date-parts") or []
        if parts and parts[0]:
            year = str(parts[0][0])
        venue = clean_text((item.get("container-title") or [""])[0])
        return {
            "source": "crossref",
            "sourceId": item.get("DOI", ""),
            "title": found_title,
            "authors": ", ".join(authors),
            "year": year,
            "venue": venue,
            "doi": norm_doi(item.get("DOI")),
            "url": item.get("URL") or "",
            "type": item.get("type") or "",
        }
    return None


def openalex_author_id(name: str) -> str | None:
    url = (
        "https://api.openalex.org/authors?"
        f"search={urllib.parse.quote(name)}&per-page=5&mailto=ev2240@nyu.edu"
    )
    try:
        data = http_json(url)
    except Exception as exc:  # noqa: BLE001
        print(f"  OpenAlex author lookup failed: {exc}", file=sys.stderr)
        return None
    results = data.get("results") or []
    for result in results:
        if (result.get("display_name") or "").strip().lower() == name.strip().lower():
            return (result.get("id") or "").rsplit("/", 1)[-1]
    if results:
        return (results[0].get("id") or "").rsplit("/", 1)[-1]
    return None


def openalex_works(author_id: str, limit: int = 1000) -> list[dict]:
    out: list[dict] = []
    cursor = "*"
    while cursor and len(out) < limit:
        url = (
            "https://api.openalex.org/works?"
            f"filter=author.id:{author_id}&per-page=200&cursor={urllib.parse.quote(cursor)}"
            "&select=id,doi,title,publication_year,authorships,primary_location,type"
            "&mailto=ev2240@nyu.edu"
        )
        try:
            data = http_json(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  OpenAlex works failed: {exc}", file=sys.stderr)
            break
        for work in data.get("results") or []:
            title = clean_text(work.get("title") or "")
            if not title:
                continue
            location = work.get("primary_location") or {}
            source = location.get("source") or {}
            venue = clean_text(source.get("display_name") or "")
            authors = []
            for authorship in work.get("authorships") or []:
                name = ((authorship.get("author") or {}).get("display_name") or "").strip()
                if name:
                    authors.append(name)
            out.append(
                {
                    "source": "openalex",
                    "sourceId": work.get("id") or "",
                    "title": title,
                    "authors": ", ".join(authors),
                    "year": str(work.get("publication_year") or ""),
                    "venue": venue,
                    "doi": norm_doi(work.get("doi")),
                    "url": location.get("landing_page_url") or "",
                    "type": work.get("type") or "",
                }
            )
            if len(out) >= limit:
                break
        cursor = (data.get("meta") or {}).get("next_cursor")
    return out


def scholar_works(author_id: str, key: str, limit: int = 200) -> list[dict]:
    out: list[dict] = []
    for start in (0, 100):
        if len(out) >= limit:
            break
        url = (
            "https://serpapi.com/search?"
            "engine=google_scholar_author"
            f"&author_id={urllib.parse.quote(author_id)}"
            f"&num=100&start={start}"
            f"&api_key={urllib.parse.quote(key)}"
        )
        try:
            data = http_json(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  SerpApi Scholar failed: {exc}", file=sys.stderr)
            break
        for article in data.get("articles") or []:
            title = clean_text(article.get("title") or "")
            if not title:
                continue
            out.append(
                {
                    "source": "scholar",
                    "sourceId": article.get("citation_id") or "",
                    "title": title,
                    "authors": clean_text(article.get("authors") or ""),
                    "year": str(article.get("year") or ""),
                    "venue": clean_text(article.get("publication") or ""),
                    "doi": "",
                    "url": "",
                    "type": "",
                }
            )
            if len(out) >= limit:
                break
        if not (data.get("articles") or []):
            break
    return out


def nips_works() -> list[dict]:
    if not NIPS.exists():
        return []
    out = []
    for item in load(NIPS):
        title = clean_text(item.get("title") or "")
        if not title:
            continue
        out.append(
            {
                "source": "nips",
                "sourceId": item.get("url") or "",
                "title": title,
                "authors": clean_text(item.get("authors") or ""),
                "year": str(item.get("year") or ""),
                "venue": clean_text(item.get("venue") or "NeurIPS"),
                "doi": "",
                "url": item.get("url") or "",
                "type": "conference",
            }
        )
    return out


def europepmc_preprints(limit: int = 500) -> list[dict]:
    """bioRxiv/medRxiv preprints indexed by Europe PMC."""
    out: list[dict] = []
    cursor = "*"
    while cursor and len(out) < limit:
        query = urllib.parse.quote('AUTH:"Erdem Varol" AND SRC:PPR')
        url = (
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
            f"query={query}&format=json&pageSize=100&resultType=lite&cursorMark={urllib.parse.quote(cursor)}"
        )
        try:
            data = http_json(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  Europe PMC failed: {exc}", file=sys.stderr)
            break
        for item in (data.get("resultList") or {}).get("result") or []:
            title = clean_text(item.get("title") or "")
            if not title:
                continue
            details = item.get("bookOrReportDetails") or {}
            venue = clean_text(details.get("publisher") or "")
            if not venue:
                venue = "bioRxiv / medRxiv"
            out.append(
                {
                    "source": "europepmc",
                    "sourceId": item.get("id") or "",
                    "title": title,
                    "authors": clean_text(item.get("authorString") or ""),
                    "year": str(item.get("pubYear") or ""),
                    "venue": venue,
                    "doi": norm_doi(item.get("doi")),
                    "url": f"https://doi.org/{norm_doi(item.get('doi'))}" if item.get("doi") else "",
                    "type": "preprint",
                }
            )
            if len(out) >= limit:
                break
        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return out


def merge_candidate(existing: dict, incoming: dict) -> dict:
    """Fill gaps without replacing a good field with an empty one."""
    merged = dict(existing)
    for field in ("title", "authors", "year", "venue", "doi", "url", "type", "sourceId"):
        if not merged.get(field) and incoming.get(field):
            merged[field] = incoming[field]
    if incoming.get("source") == "nips" and incoming.get("url"):
        merged["url"] = incoming["url"]
        if incoming.get("venue"):
            merged["venue"] = incoming["venue"]
    sources = set((merged.get("sources") or [merged.get("source", "")]))
    if incoming.get("source"):
        sources.add(incoming["source"])
    merged["sources"] = sorted(s for s in sources if s)
    return merged


def dedupe_candidates(candidates: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for candidate in candidates:
        if not candidate.get("title"):
            continue
        doi = norm_doi(candidate.get("doi"))
        key = f"doi:{doi}" if doi else f"title:{norm_title(candidate['title'])}"
        if key in merged:
            merged[key] = merge_candidate(merged[key], candidate)
        else:
            candidate = dict(candidate)
            candidate["sources"] = [candidate.get("source", "")]
            merged[key] = candidate
    # A DOI candidate and a title-only candidate can be the same paper. Collapse
    # by title after the DOI pass, keeping the DOI-bearing record.
    by_title: dict[str, dict] = {}
    for candidate in merged.values():
        key = norm_title(candidate["title"])
        if key not in by_title:
            by_title[key] = candidate
        elif not by_title[key].get("doi") and candidate.get("doi"):
            by_title[key] = merge_candidate(candidate, by_title[key])
        else:
            by_title[key] = merge_candidate(by_title[key], candidate)
    return list(by_title.values())


def candidate_entry(candidate: dict) -> dict:
    entry = {
        "year": str(candidate.get("year") or ""),
        "title": candidate.get("title") or "",
        "authors": candidate.get("authors") or "",
        "venue": candidate.get("venue") or "",
    }
    if candidate.get("doi"):
        entry["doi"] = norm_doi(candidate["doi"])
    if candidate.get("url"):
        entry["url"] = candidate["url"]
    return entry


def year_rank(year: str) -> int:
    match = re.match(r"(\d{4})", str(year))
    if match:
        return int(match.group(1))
    return 0


def insert_entry(publications: list[dict], entry: dict) -> None:
    same = [i for i, pub in enumerate(publications) if pub.get("year") == entry.get("year")]
    if same:
        publications.insert(same[-1] + 1, entry)
        return
    rank = year_rank(entry.get("year", ""))
    index = next(
        (i for i, pub in enumerate(publications) if year_rank(pub.get("year", "")) < rank),
        len(publications),
    )
    publications.insert(index, entry)


def find_baseline(
    candidate: dict, publications: list[dict], dois: dict
) -> list[dict]:
    doi = norm_doi(candidate.get("doi"))
    title = norm_title(candidate.get("title", ""))
    matches = []
    if doi:
        for pub in publications:
            pub_doi = norm_doi(pub.get("doi")) or norm_doi(
                (dois.get(norm_title(pub.get("title", ""))) or {}).get("doi")
            )
            if pub_doi and pub_doi == doi:
                matches.append(pub)
    if matches:
        return matches
    if title:
        matches = [
            pub for pub in publications if norm_title(pub.get("title", "")) == title
        ]
    return matches


def build_review(
    site: dict, dois: dict, candidates: list[dict], config: dict, allow_network: bool = True
) -> dict:
    publications = site.get("publications") or []
    excluded = {norm_title(title) for title in config.get("excludedTitles") or []}
    changes = []
    skipped = []
    counts = Counter()

    for candidate in candidates:
        title_key = norm_title(candidate.get("title", ""))
        if title_key in excluded:
            skipped.append(
                {
                    "title": candidate.get("title"),
                    "year": candidate.get("year"),
                    "reason": "excluded by publications.config.json",
                    "source": candidate.get("source"),
                }
            )
            counts["skipped"] += 1
            continue

        title_lower = clean_text(candidate.get("title", "")).lower()
        if title_lower.startswith(BAD_TITLE_PREFIXES) or candidate.get("type") in BAD_TYPES:
            skipped.append(
                {
                    "title": candidate.get("title"),
                    "year": candidate.get("year"),
                    "reason": "non-paper record (editorial/response/correction)",
                    "source": candidate.get("source"),
                }
            )
            counts["skipped"] += 1
            continue

        # Prompt noise from Scholar is useful for discovery but not for adding
        # new rows. A new or replacement row needs a DOI or an official NeurIPS
        # URL, per the exact-DOI decision.
        if not candidate.get("doi") and candidate.get("source") != "nips":
            skipped.append(
                {
                    "title": candidate.get("title"),
                    "year": candidate.get("year"),
                    "reason": "no DOI or official proceedings URL",
                    "source": candidate.get("source"),
                }
            )
            counts["skipped"] += 1
            continue

        matches = find_baseline(candidate, publications, dois)
        if not matches:
            entry = candidate_entry(candidate)
            if not entry["year"]:
                entry["year"] = str(candidate.get("year") or "")
            changes.append(
                {
                    "kind": "NEW",
                    "title": entry["title"],
                    "year": entry["year"],
                    "source": candidate.get("source"),
                    "sources": candidate.get("sources") or [candidate.get("source")],
                    "confidence": "exact DOI" if candidate.get("doi") else "normalized title",
                    "before": None,
                    "after": entry,
                }
            )
            counts["new"] += 1
            continue

        # A published version wins over a preprint. If the baseline has both,
        # keep the published row and remove the preprint row.
        published_matches = [pub for pub in matches if not is_preprint(pub)]
        preprint_matches = [pub for pub in matches if is_preprint(pub)]
        candidate_is_preprint = is_preprint(candidate)

        if candidate_is_preprint and published_matches:
            skipped.append(
                {
                    "title": candidate.get("title"),
                    "year": candidate.get("year"),
                    "reason": "published version already present",
                    "source": candidate.get("source"),
                }
            )
            counts["skipped"] += 1
            continue

        if not candidate_is_preprint and preprint_matches and not published_matches:
            before = preprint_matches[0]
            after = candidate_entry(candidate)
            if not after.get("venue"):
                after["venue"] = before.get("venue", "")
            if not after.get("authors"):
                after["authors"] = before.get("authors", "")
            changes.append(
                {
                    "kind": "REPLACE",
                    "title": after["title"],
                    "year": after["year"],
                    "source": candidate.get("source"),
                    "sources": candidate.get("sources") or [candidate.get("source")],
                    "confidence": "exact DOI" if candidate.get("doi") else "normalized title",
                    "before": before,
                    "after": after,
                    "reason": "preprint replaced by published version (policy 1)",
                }
            )
            counts["replace"] += 1
            continue

        before = (published_matches or matches)[0]
        after = dict(before)
        reasons: list[str] = []
        candidate_doi = norm_doi(candidate.get("doi"))
        current_doi = norm_doi(before.get("doi")) or norm_doi(
            (dois.get(norm_title(before.get("title", ""))) or {}).get("doi")
        )
        before_is_preprint = is_preprint(before) or current_doi.startswith(
            ("10.1101/", "10.21203/", "10.48550/arxiv.")
        )
        if candidate_doi and candidate_doi != current_doi:
            upgrade = (
                not current_doi
                or (before_is_preprint and not candidate_is_preprint)
                or (not before_is_preprint and not candidate_is_preprint)
            )
            if upgrade:
                after["doi"] = candidate_doi
                reasons.append("DOI update")

        candidate_url = candidate.get("url")
        current_link = entry_link(before, dois)
        blocked_url = candidate_url and "10.52202/" in candidate_url
        same_doi = (
            candidate_url
            and current_doi
            and norm_doi(candidate_url) == current_doi
        )
        if (
            candidate_url
            and not blocked_url
            and not same_doi
            and candidate_url != current_link
            and (not current_link or candidate.get("source") == "nips")
        ):
            after["url"] = candidate_url
            reasons.append("Open official URL")
        if reasons:
            changes.append(
                {
                    "kind": "UPDATED",
                    "title": before.get("title"),
                    "year": before.get("year"),
                    "source": candidate.get("source"),
                    "sources": candidate.get("sources") or [candidate.get("source")],
                    "confidence": "exact DOI" if candidate.get("doi") else "normalized title",
                    "before": before,
                    "after": after,
                    "reason": "; ".join(reasons),
                }
            )
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1

    # Remove a preprint row when a published row with the same normalized title
    # is already in the baseline. This makes the policy idempotent.
    grouped: dict[str, list[dict]] = {}
    for pub in publications:
        grouped.setdefault(norm_title(pub.get("title", "")), []).append(pub)
    for group in grouped.values():
        preprints = [pub for pub in group if is_preprint(pub)]
        published = [pub for pub in group if not is_preprint(pub)]
        if preprints and published:
            for preprint in preprints:
                changes.append(
                    {
                        "kind": "REMOVE",
                        "title": preprint.get("title"),
                        "year": preprint.get("year"),
                        "source": "policy",
                        "confidence": "normalized title",
                        "before": preprint,
                        "after": None,
                        "reason": "preprint already superseded by a published version (policy 1)",
                    }
                )
                counts["removed"] += 1

    # DOI refresh for baseline entries that have no usable link. Exact title
    # match only, per the 2026-11-12 decision.
    doi_updates = []
    if allow_network:
        for pub in publications:
            if pub.get("doi") or pub.get("url") or entry_link(pub, dois):
                continue
            found = crossref_search(pub.get("title", ""))
            if not found or not found.get("doi"):
                continue
            doi_updates.append(
                {
                    "key": norm_title(pub.get("title", "")),
                    "doi": found["doi"],
                    "title": pub.get("title", ""),
                    "year": pub.get("year", ""),
                    "matchedTitle": found.get("title", ""),
                    "source": "crossref",
                    "confidence": "exact normalized title",
                }
            )

    return {
        "generatedAt": now_iso(),
        "baselineHash": hashlib.sha256(SITE.read_text(encoding="utf-8").encode()).hexdigest(),
        "baselineCount": len(publications),
        "config": config,
        "summary": {
            "candidates": len(candidates),
            **dict(counts),
            "doiUpdates": len(doi_updates),
        },
        "changes": changes,
        "doiUpdates": doi_updates,
        "skipped": skipped,
    }


def fmt_entry(entry: dict | None) -> str:
    if not entry:
        return "—"
    parts = [
        f"**{entry.get('title', '')}**",
        f"{entry.get('year', '')} · {entry.get('venue', '')}",
    ]
    if entry.get("doi"):
        parts.append(f"DOI: `{entry['doi']}`")
    if entry.get("url"):
        parts.append(f"[official page]({entry['url']})")
    return "<br>".join(parts)


def write_diff(review: dict) -> None:
    lines = [
        "# Publications review diff",
        "",
        f"Generated: {review['generatedAt']}",
        f"Baseline: {review['baselineCount']} publications",
        "",
        "## Summary",
        "",
        "| Item | Count |",
        "|---|---:|",
        f"| Candidates fetched | {review['summary'].get('candidates', 0)} |",
        f"| New | {review['summary'].get('new', 0)} |",
        f"| Updated | {review['summary'].get('updated', 0)} |",
        f"| Replaced | {review['summary'].get('replace', 0)} |",
        f"| Removed | {review['summary'].get('removed', 0)} |",
        f"| Unchanged | {review['summary'].get('unchanged', 0)} |",
        f"| Skipped | {review['summary'].get('skipped', 0)} |",
        f"| DOI additions | {review['summary'].get('doiUpdates', 0)} |",
        "",
    ]
    changes = review.get("changes") or []
    if not changes and not review.get("doiUpdates"):
        lines += ["No proposed publication changes.", ""]
    else:
        for kind in ("NEW", "UPDATED", "REPLACE", "REMOVE"):
            rows = [change for change in changes if change["kind"] == kind]
            if not rows:
                continue
            lines += [f"## {kind}", ""]
            for change in rows:
                lines += [
                    f"### {change.get('title', '')}",
                    "",
                    f"- Source: `{change.get('source', '')}`",
                    f"- Confidence: {change.get('confidence', '')}",
                ]
                if change.get("reason"):
                    lines.append(f"- Reason: {change['reason']}")
                if change.get("before") is not None:
                    lines.append(f"- Before: {fmt_entry(change['before'])}")
                if change.get("after") is not None:
                    lines.append(f"- After: {fmt_entry(change['after'])}")
                lines.append("")
        if review.get("doiUpdates"):
            lines += ["## DOI additions", "", "| Year | Title | DOI | Source |", "|---|---|---|---|"]
            for update in review["doiUpdates"]:
                lines.append(
                    f"| {update.get('year', '')} | {update.get('title', '')} | `{update.get('doi', '')}` | {update.get('source', '')} |"
                )
            lines.append("")

    if review.get("skipped"):
        lines += ["## Skipped", "", "| Year | Title | Reason |", "|---|---|---|"]
        for item in review["skipped"]:
            lines.append(
                f"| {item.get('year', '')} | {item.get('title', '')} | {item.get('reason', '')} |"
            )
        lines.append("")

    DIFF.write_text("\n".join(lines), encoding="utf-8")


def write_pr_body(review: dict) -> None:
    summary = review["summary"]
    body = [
        "## Monthly publications refresh",
        "",
        f"Generated: `{review['generatedAt']}`",
        "",
        "| Result | Count |",
        "|---|---:|",
        f"| New | {summary.get('new', 0)} |",
        f"| Updated | {summary.get('updated', 0)} |",
        f"| Replaced | {summary.get('replace', 0)} |",
        f"| Removed | {summary.get('removed', 0)} |",
        f"| DOI additions | {summary.get('doiUpdates', 0)} |",
        f"| Skipped | {summary.get('skipped', 0)} |",
        "",
        "Full review: [`publications-review/diff.md`](publications-review/diff.md)  ",
        "Machine-readable review: [`publications-review/review.json`](publications-review/review.json)",
        "",
        "## Screenshots",
        "",
        f"![Desktop publications](SCREENSHOT_BASE/desktop-publications.png)",
        "",
        f"![Desktop full page](SCREENSHOT_BASE/desktop-full.jpg)",
        "",
        f"![Mobile publications](SCREENSHOT_BASE/mobile-publications.png)",
        "",
        "## Decisions applied",
        "",
        "- Strategy B: fetch and match, then review the diff.",
        "- Approval is this GitHub PR; nothing is auto-merged.",
        "- Preprint policy 1: a published version replaces its preprint row.",
        "- Venue display is a short label plus year.",
        "- NeurIPS 2026: the first two papers are included; the third is excluded.",
        "",
        "<!-- DOI-AUDIT -->",
        "",
        "## Approval",
        "",
        "**Erdem Varol must approve this PR before merge.**",
        "",
    ]
    PR_BODY.write_text("\n".join(body), encoding="utf-8")


def apply_review(review: dict) -> None:
    site = load(SITE)
    dois = load(DOIS)
    current_hash = hashlib.sha256(SITE.read_text(encoding="utf-8").encode()).hexdigest()
    if review.get("baselineHash") != current_hash:
        raise SystemExit(
            "Refusing to apply: site.json changed after the review was generated. "
            "Re-run sync and review the new diff."
        )

    publications = site.get("publications") or []
    removed = 0
    replaced = 0
    added = 0
    updated = 0

    for change in review.get("changes") or []:
        kind = change.get("kind")
        before = change.get("before")
        after = change.get("after")
        if kind == "REMOVE" and before:
            publications[:] = [
                pub
                for pub in publications
                if not (
                    pub.get("year") == before.get("year")
                    and pub.get("title") == before.get("title")
                )
            ]
            removed += 1
        elif kind == "REPLACE" and before and after:
            publications[:] = [
                pub
                for pub in publications
                if not (
                    pub.get("year") == before.get("year")
                    and pub.get("title") == before.get("title")
                )
            ]
            insert_entry(publications, after)
            replaced += 1
        elif kind == "NEW" and after:
            insert_entry(publications, after)
            added += 1
        elif kind == "UPDATED" and before and after:
            for index, pub in enumerate(publications):
                if (
                    pub.get("year") == before.get("year")
                    and pub.get("title") == before.get("title")
                ):
                    publications[index] = after
                    updated += 1
                    break

    site["publications"] = publications

    for update in review.get("doiUpdates") or []:
        dois[update["key"]] = {
            "doi": update["doi"],
            "title": update["title"],
            "year": update["year"],
            "similarity": 1.0,
            "varol": True,
            "source": update["source"],
            "confidence": update["confidence"],
            "matchedTitle": update["matchedTitle"],
            "updatedAt": review["generatedAt"],
        }

    dump(SITE, site)
    dump(DOIS, dois)
    print(
        f"Applied: {added} added, {updated} updated, {replaced} replaced, "
        f"{removed} removed, {len(review.get('doiUpdates') or [])} DOI additions."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply the reviewed diff")
    parser.add_argument("--offline", action="store_true", help="skip network adapters")
    parser.add_argument("--limit", type=int, default=1000, help="max OpenAlex works")
    args = parser.parse_args()

    config = load(CONFIG)
    if args.apply:
        review = load(REVIEW)
        apply_review(review)
        return

    site = load(SITE)
    dois = load(DOIS)
    candidates: list[dict] = []
    errors: list[str] = []

    if not args.offline:
        if config.get("sources", {}).get("openalex", True):
            author_id = openalex_author_id(config.get("openalexAuthor", "Erdem Varol"))
            if author_id:
                print(f"OpenAlex author: {author_id}")
                works = openalex_works(author_id, limit=args.limit)
                print(f"OpenAlex works: {len(works)}")
                candidates.extend(works)
            else:
                errors.append("OpenAlex author not found")

        if config.get("sources", {}).get("scholar", True):
            key = get_serp_key()
            if key:
                works = scholar_works(config.get("serpApiAuthorId", ""), key)
                print(f"Scholar works: {len(works)}")
                candidates.extend(works)
            else:
                print("SERPAPI_KEY not set; skipping Scholar.", file=sys.stderr)

        if config.get("sources", {}).get("nips", True):
            works = nips_works()
            print(f"NeurIPS works: {len(works)}")
            candidates.extend(works)

        if config.get("sources", {}).get("europepmc", True):
            works = europepmc_preprints()
            print(f"Preprints (Europe PMC): {len(works)}")
            candidates.extend(works)

    candidates = dedupe_candidates(candidates)
    print(f"Unique candidates: {len(candidates)}")
    review = build_review(site, dois, candidates, config, allow_network=not args.offline)
    review["errors"] = errors
    dump(REVIEW, review)
    write_diff(review)
    write_pr_body(review)
    print(json.dumps(review["summary"], indent=2))
    print(f"Wrote {REVIEW.relative_to(ROOT)}, {DIFF.relative_to(ROOT)}, {PR_BODY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
