#!/usr/bin/env python3
"""Turn the crawled course pages into structured JSON for the Astro site.

The old Squarespace course pages are mostly prose plus one schedule table. We
keep that shape: sanitized HTML for the prose (links included), and the table
as rows of sanitized cells. Run after re-crawling:

    python3 scripts/sync-courses.py
"""
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Tag

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT.parent / "_crawl" / "raw"
OUT = ROOT / "src" / "data" / "courses.json"

# old Squarespace file links -> local files copied into public/docs/
DOCS = {
    "neuroinformatics_syllabus.pdf": "neuroinformatics_syllabus.pdf",
    "neuroinformatics_syllabus-ywpa.pdf": "neuroinformatics_syllabus-ywpa.pdf",
    "Syllabus-Computer-Vision-Fall-24.pdf": "Syllabus-Computer-Vision-Fall-24.pdf",
    "Syllabus-Computer-Vision-Fall-25.pdf": "Syllabus-Computer-Vision-Fall-25.pdf",
    "Syllabus-Computer-Vision-Fall-2026.pdf": "Syllabus-Computer-Vision-Fall-2026.pdf",
    "nyu_utsw_postdoc_ad.pdf": "nyu_utsw_postdoc_ad.pdf",
}

COURSES = [
    # source file, slug, legacy path, short label
    ("neuroinformatics-cs-gy-9223-spring26.html", "neuroinformatics-spring26", "/neuroinformatics-cs-gy-9223-spring26", "Neuroinformatics · Spring 2026"),
    ("neuroinformatics-cs-gy-9223.html", "neuroinformatics-spring25", "/neuroinformatics-cs-gy-9223", "Neuroinformatics · Spring 2025"),
    ("neuroinformatics-cs-gy-9223-spring24.html", "neuroinformatics-spring24", "/neuroinformatics-cs-gy-9223-spring24", "Neuroinformatics · Spring 2024"),
    ("computer-vision-cs-gy-6643-2026.html", "computer-vision-fall26", "/computer-vision-cs-gy-6643-2026", "Computer Vision · Fall 2026"),
    ("computer-vision-cs-gy-6643-1.html", "computer-vision-fall25", "/computer-vision-cs-gy-6643-1", "Computer Vision · Fall 2025"),
    ("computer-vision-cs-gy-6643.html", "computer-vision-fall24", "/computer-vision-cs-gy-6643", "Computer Vision · Fall 2024"),
]

ALLOWED = {"p", "h4", "ul", "ol", "li", "strong", "b", "em", "i", "u", "a", "br", "span"}

# Old course URLs (absolute or root-relative) -> new Astro routes.
LEGACY = {
    "/neuroinformatics-cs-gy-9223-spring26": "/teaching/neuroinformatics-spring26",
    "/neuroinformatics-cs-gy-9223-spring24": "/teaching/neuroinformatics-spring24",
    "/neuroinformatics-cs-gy-9223": "/teaching/neuroinformatics-spring25",
    "/computer-vision-cs-gy-6643-2026": "/teaching/computer-vision-fall26",
    "/computer-vision-cs-gy-6643-1": "/teaching/computer-vision-fall25",
    "/computer-vision-cs-gy-6643": "/teaching/computer-vision-fall24",
}


def clean_text(s):
    return " ".join(s.split())


def local_href(href):
    """Point old course and /s/*.pdf links at the rebuilt site."""
    if not href:
        return ""
    href = href.strip()
    for old, new in LEGACY.items():
        if href == old or href.endswith(old) or href.endswith(old + "/"):
            return new
    if href.startswith("/s/"):
        name = href[3:]
        if name in DOCS:
            return f"/docs/{DOCS[name]}"
        return f"/docs/{name}"
    if href.startswith(("http://", "https://", "mailto:", "#", "/")):
        return href
    return ""


def sanitize(node, soup):
    """Return HTML for a tag with only the tags/attributes the site supports."""
    clone = BeautifulSoup(str(node), "html.parser")
    for bad in clone(["script", "style", "iframe", "form", "input", "button", "svg"]):
        bad.decompose()
    for tag in clone.find_all(True):
        if tag.name not in ALLOWED:
            tag.unwrap()
            continue
        attrs = {}
        if tag.name == "a":
            href = local_href(tag.get("href", ""))
            if href:
                attrs["href"] = href
                if href.startswith(("http://", "https://")):
                    attrs["target"] = "_blank"
                    attrs["rel"] = "noopener"
        tag.attrs = attrs
    body = clone.body or clone
    out = "".join(str(c) for c in body.children)
    out = re.sub(r"<p[^>]*>\s*(&nbsp;|\s)*</p>", "", out)
    return out.strip()


def parse(path):
    soup = BeautifulSoup(path.read_text("utf-8"), "html.parser")
    main = soup.find("main") or soup.body
    h1 = main.find("h1")
    title = clean_text(h1.get_text(" ")) if h1 else path.stem

    terms = main.find_all(["h4", "p"])
    term_el = next((h for h in terms if re.fullmatch(r"(Spring|Fall|Summer|Winter)\s+20\d\d", clean_text(h.get_text(" ")))), None)
    term = clean_text(term_el.get_text(" ")) if term_el else ""

    headings = main.find_all(["h3", "h4"])
    sched_el = next((h for h in headings if h.get_text(strip=True).lower().startswith("schedule")), None)
    reads_el = next((h for h in headings if "essential read" in h.get_text(strip=True).lower()), None)

    # Overview: everything after the title up to the schedule table. This keeps
    # the course team, term, description, course-information block and syllabus.
    overview = []
    stop = sched_el or reads_el
    for el in h1.next_elements if h1 else []:
        if stop is not None and el is stop:
            break
        if not isinstance(el, Tag):
            continue
        if el.name in ("p", "h4", "ul", "ol"):
            # skip children whose parent we already captured
            if el.find_parent(["p", "ul", "ol"]):
                continue
            if el is term_el:
                continue
            html = sanitize(el, soup)
            if clean_text(BeautifulSoup(html, "html.parser").get_text(" ")):
                overview.append(html)

    schedule = {"headers": [], "rows": []}
    table = sched_el.find_next("table") if sched_el else None
    if table:
        head = table.find("thead")
        if head:
            schedule["headers"] = [sanitize(th, soup) for th in head.find_all("th")]
        body = table.find("tbody") or table
        for tr in body.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            row = [sanitize(c, soup) for c in cells]
            if any(clean_text(BeautifulSoup(c, "html.parser").get_text(" ")) for c in row):
                schedule["rows"].append(row)

    reads = []
    if reads_el:
        for el in reads_el.next_elements:
            if not isinstance(el, Tag):
                continue
            if el.name in ("p", "h4", "ul", "ol", "li"):
                if el.find_parent(["p", "ul", "ol"]):
                    continue
                html = sanitize(el, soup)
                if clean_text(BeautifulSoup(html, "html.parser").get_text(" ")):
                    reads.append(html)

    # Short summary: the description paragraphs after the term, before
    # "Course information" (or the first TA / instructor block).
    summary = []
    if term_el:
        for el in term_el.find_all_next(["p"]):
            if sched_el and el is sched_el:
                break
            t = clean_text(el.get_text(" "))
            if not t:
                continue
            if t.lower().startswith(("course information", "ta:", "instructor:", "syllabus")):
                break
            if el.find("strong") and t == clean_text(el.find("strong").get_text(" ")):
                summary.append(sanitize(el, soup))
                continue
            summary.append(sanitize(el, soup))
            if len(summary) >= 3:
                break

    syllabus = ""
    previous = ""
    for a in main.find_all("a", href=True):
        label = clean_text(a.get_text(" ")).lower()
        href = local_href(a["href"])
        if not syllabus and ("syllabus" in label or "Syllabus" in a["href"]):
            syllabus = href
        if not previous and "previous iteration" in clean_text(a.parent.get_text(" ")).lower():
            previous = href
    if not syllabus:
        cand = main.find("a", href=re.compile(r"Syllabus", re.I))
        syllabus = local_href(cand["href"]) if cand else ""

    return {
        "title": title,
        "term": term,
        "summary": summary,
        "overview": overview,
        "schedule": schedule,
        "reads": reads,
        "syllabus": syllabus,
        "previous": previous,
    }


def main():
    out = {}
    for fn, slug, legacy, label in COURSES:
        data = parse(RAW / fn)
        data["slug"] = slug
        data["legacy"] = legacy
        data["label"] = label
        out[slug] = data
        print(f"{slug}: {len(data['overview'])} overview blocks, {len(data['schedule']['rows'])} schedule rows, {len(data['reads'])} reading blocks")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
