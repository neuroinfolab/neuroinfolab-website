# Neuroinformatics Lab site


Development Setup

```bash
pnpm install
pnpm dev        # http://localhost:4321
pnpm build      # -> dist/
pnpm preview    # serve dist/
```

## Layout

```
public/
  docs/           CV, syllabi, postdoc ad
  img/            team, alumni, lab life, courses, logos
  media/          posters, Forecasting Motion GIF
  media/loops/    5 hero WebM loops + MP4 fallbacks
src/
  components/     Header, Footer, ProjectCard, CoursePage
  data/           site.json, course-schedules/*.toml, dois.json, nips.json,
                  featured-publications.json, publications.config.json
  layouts/        Base.astro
  lib/            url.ts, course-schedule.ts
  pages/          index.astro, 404.astro, and term pages per course
  styles/         global.css
scripts/          sync_publications.py, check_publications.py,
                  publication-screenshots.mjs, scrape_nips.py, serp.py,
                  shots.mjs
```

## Pages

| Route | Contents |
|---|---|
| `/` | Hero carousel, PI bio, team, alumni, Lab life, publications, funding, openings |
| `/neuroinformatics/spring-2026` | Neuroinformatics (CS-GY 9223 / CS-UY 3943), Spring 2026 |
| `/neuroinformatics/spring-2025` | Archived Neuroinformatics schedule, Spring 2025 |
| `/neuroinformatics/spring-2024` | Archived Neuroinformatics schedule, Spring 2024 |
| `/computer-vision/fall-2026` | Computer Vision (CS-GY 6643), Fall 2026 |
| `/computer-vision/fall-2025` | Archived Computer Vision schedule, Fall 2025 |
| `/computer-vision/fall-2024` | Archived Computer Vision schedule, Fall 2024 |
| `/404` | Custom not-found page (emitted as `404.html`) |

Components: `src/components/CoursePage.astro`. 

Course schedules are stored in `src/data/course-schedules/<course>-<term>.toml`, including the archived offerings, and loaded through `src/lib/course-schedule.ts`. The rest of each course page stays in its `.astro` frontmatter.

## Data

| File | Purpose |
|---|---|
| `src/data/site.json` | Publications, team, alumni, projects, funding objects, bio. |
| `src/data/course-schedules/*.toml` | One schedule per course offering, current and archived: a `[[schedule]]` table per class meeting. |
| `src/data/dois.json` | DOI matches keyed by title; per-entry `doi`/`url` fields in `site.json` |
| `src/data/publications.config.json` | Locked refresh policy: strategy B, GitHub PR, monthly cron, preprint policy 1, exact DOI/title matching, excluded titles. |
| `src/data/featured-publications.json` | Curated top-K publication list, grouped by topic for the home page. Each entry points at an image in `public/img/pubs/`. |

Publication links resolve in this order: per-entry `url`, per-entry `doi`,
title lookup in `dois.json`.

Preprint policy is **1**: keep a preprint until a published version exists,
then remove the preprint row and show the published version. The
removed titles are listed in `excludedTitles`.

## Publications refresh

The monthly pipeline is implemented:

```bash
pnpm publications:sync    # fetch, normalize, match, write publications-review/
pnpm publications:apply   # apply the reviewed diff to site.json / dois.json
pnpm publications:check   # resolve links; write links.json and links.md
pnpm publications:shots   # screenshot the publications list
```

`publications:sync` writes:

- `publications-review/review.json` — machine-readable changes.
- `publications-review/diff.md` — human-readable NEW / UPDATED / REPLACE / REMOVE / SKIPPED diff.
- `publications-review/pr-body.md` — PR summary with screenshot placeholders.

`publications:apply` refuses to run if `site.json` changed after the review was generated. It preserves team, alumni, projects, funding, and award notes.

## Adding content

**A featured publication**: add the paper to
`src/data/featured-publications.json`, put a square-ish figure in
`public/img/pubs/`, and use a topic id from that file. The title must match
`src/data/site.json` after punctuation normalization. The home page no longer renders the Projects section

**A person**: drop a 4:5 JPEG in `public/img/team/` or `public/img/alumni/`,
add the entry to `src/data/site.json`, and add the image mapping in
`src/pages/index.astro`. Use `public/img/team/placeholder.svg` when a portrait
is not available yet.

**A course schedule**: edit the term's file in `src/data/course-schedules/`.
To add a term, copy the closest existing TOML file, add a route under
`src/pages/<course>/` that calls `getSchedule('<course>-<term>')`, and put the
rest of the page copy in that route's frontmatter. Archived terms use the same
format.

**A publication**: edit `src/data/site.json` directly. Add a per-entry `doi` or
`url` when the title-keyed lookup is wrong or a better official link exists.
Keep `note` short (Spotlight, Oral Presentation, Top 3% of papers). The monthly
pipeline will propose new papers for review; use
`src/data/publications.config.json` for titles that must never be imported.

### Search indexing

- **Production:** `public/robots.txt` allows all crawlers and points at
  `https://www.neuroinformaticslab.com/sitemap-index.xml`.
- **Sitemap:** `@astrojs/sitemap` emits `sitemap-index.xml` plus shards at build
  time. The 404 page is excluded.
- **Preview:** `Base.astro` emits `noindex, nofollow` whenever the build host is
  not `neuroinformaticslab.com` or `www.neuroinformaticslab.com`, so the GitHub
  Pages project URL never competes with the real domain in search.
- The meta tag, not `robots.txt`, is what excludes the preview: crawlers only
  read `robots.txt` from the origin root, not from `/neuroinfolab-website/`.
