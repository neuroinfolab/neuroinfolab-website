#!/usr/bin/env python3
"""Resolve every publication link and write a link audit for the PR.

The audit records the URL the DOI or official page ultimately opens. Publisher
sites often block automated requests with 403/429; those are recorded as
"blocked" rather than "broken", because the redirect target is still useful.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "src" / "data" / "site.json"
DOIS = ROOT / "src" / "data" / "dois.json"
REVIEW = ROOT / "publications-review" / "review.json"
OUT_JSON = ROOT / "publications-review" / "links.json"
OUT_MD = ROOT / "publications-review" / "links.md"
PR_BODY = ROOT / "publications-review" / "pr-body.md"
UA = "Mozilla/5.0 (compatible; neuroinformaticslab-site/1.0; +https://www.neuroinformaticslab.com)"
BLOCKED = {401, 403, 406, 429, 503, 999}


def clean_text(value) -> str:
    value = re.sub(r"<[^>]+>", "", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def norm_title(value: str) -> str:
    value = clean_text(value).lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def norm_doi(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "https://dx.doi.org/"):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value.removeprefix("doi:").strip()


def link_for(publication: dict, dois: dict) -> str | None:
    if publication.get("url"):
        return publication["url"]
    doi = norm_doi(publication.get("doi")) or norm_doi(
        (dois.get(norm_title(publication.get("title", ""))) or {}).get("doi")
    )
    if not doi or doi.startswith("10.52202/"):
        return None
    return f"https://doi.org/{doi}"


def check(link: str, timeout: int = 30) -> dict:
    request = urllib.request.Request(link, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "link": link,
                "status": response.status,
                "final": response.geturl(),
                "blocked": response.status in BLOCKED,
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        return {
            "link": link,
            "status": exc.code,
            "final": exc.geturl() if hasattr(exc, "geturl") else link,
            "blocked": exc.code in BLOCKED,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "link": link,
            "status": "ERR",
            "final": "",
            "blocked": False,
            "error": str(exc)[:180],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    site = json.loads(SITE.read_text(encoding="utf-8"))
    dois = json.loads(DOIS.read_text(encoding="utf-8"))
    publications = site.get("publications") or []

    rows = []
    for publication in publications:
        link = link_for(publication, dois)
        rows.append(
            {
                "year": publication.get("year", ""),
                "title": publication.get("title", ""),
                "link": link,
                "doi": norm_doi(publication.get("doi"))
                or norm_doi((dois.get(norm_title(publication.get("title", ""))) or {}).get("doi")),
            }
        )

    links = [row for row in rows if row["link"]]
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(check, row["link"], args.timeout): row for row in links}
        for future in concurrent.futures.as_completed(futures):
            row = futures[future]
            result = future.result()
            results.append({**row, **result})

    results.sort(key=lambda item: (item.get("year", ""), item.get("title", "")), reverse=True)
    total = len(results)
    ok = sum(1 for item in results if item["status"] == 200)
    blocked = sum(1 for item in results if item["blocked"])
    errors = sum(1 for item in results if item["status"] == "ERR")
    other = total - ok - blocked - errors

    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "total": total,
        "ok": ok,
        "blocked": blocked,
        "errors": errors,
        "other": other,
        "links": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Publication link audit",
        "",
        f"Generated: {payload['generatedAt']}",
        "",
        f"- Links checked: {total}",
        f"- 200 OK: {ok}",
        f"- Publisher bot-blocks (401/403/406/429/503): {blocked}",
        f"- Connection errors: {errors}",
        f"- Other statuses: {other}",
        "",
        "| Year | Paper | Recorded link | HTTP | Opens |",
        "|---|---|---|---:|---|",
    ]
    for item in results:
        target = item["final"] or item["error"] or "—"
        lines.append(
            f"| {item['year']} | {item['title']} | {item['link']} | {item['status']} | {target} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Append a compact changed-paper audit to the PR body. Replace a previous
    # section if the workflow is re-run.
    changed = []
    if REVIEW.exists():
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        changed = review.get("changes") or []
    changed_rows = []
    for change in changed:
        candidate = change.get("after") or change.get("before") or {}
        title = candidate.get("title")
        if not title:
            continue
        match = next(
            (
                item
                for item in results
                if norm_title(item.get("title", "")) == norm_title(title)
            ),
            None,
        )
        if match:
            changed_paper = change.get("after") or change.get("before")
            changed_rows.append(
                f"| {match.get('year', '')} | {title} | `{match.get('doi') or '—'}` | "
                f"{match['status']} | {match['final'] or match['error'] or '—'} |"
            )

    audit = [
        "<!-- DOI-AUDIT -->",
        "## DOI link audit",
        "",
        f"- {total} publication links checked.",
        f"- {ok} returned 200; {blocked} were publisher bot-blocks; {errors} connection errors; {other} other statuses.",
        f"- Full audit: [`publications-review/links.md`](publications-review/links.md)",
        "",
    ]
    if changed_rows:
        audit += [
            "| Year | Changed paper | DOI | HTTP | Opens |",
            "|---|---|---|---:|---|",
            *changed_rows,
            "",
        ]
    audit_text = "\n".join(audit)
    body = PR_BODY.read_text(encoding="utf-8") if PR_BODY.exists() else ""
    if "<!-- DOI-AUDIT -->" in body:
        body = body.split("<!-- DOI-AUDIT -->", 1)[0].rstrip() + "\n\n" + audit_text
    else:
        body = body.rstrip() + "\n\n" + audit_text
    PR_BODY.write_text(body.rstrip() + "\n", encoding="utf-8")

    print(
        f"{total} links: {ok} OK, {blocked} blocked, {errors} errors, {other} other. "
        f"Wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}."
    )


if __name__ == "__main__":
    main()
