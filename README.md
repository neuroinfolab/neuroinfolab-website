# neuroinfolab-demo

The Neuroinformatics Lab site: Astro 7, static output, no backend or runtime
dependencies. Most content is JSON; the course schedules and readings live in
the course page frontmatter.

**Live:** https://pxndey.github.io/neuroinfolab-demo/ (public — the Pages
workflow disables the passcode gate)
**Repo:** https://github.com/pxndey/neuroinfolab-demo

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
  media/          posters, source clips, Forecasting Motion GIF
  media/loops/    5 hero WebM loops + MP4 fallbacks
src/
  components/     Header, Footer, ProjectCard, CoursePage
  data/           site.json, dois.json, nips.json, publications.config.json
  layouts/        Base.astro
  lib/            url.ts
  pages/          index.astro, neuroinformatics.astro, computer-vision.astro
  styles/         global.css
  content/        reserved first-pass project files (not rendered)
scripts/          sync_publications.py, check_publications.py,
                  publication-screenshots.mjs, scrape_nips.py, serp.py,
                  sync-site-text.py, shots.mjs
```

## Pages

| Route | Contents |
|---|---|
| `/` | Hero carousel, PI bio, team, alumni, Lab life, projects, publications, funding, openings |
| `/neuroinformatics` | Neuroinformatics (CS-GY 9223 / CS-UY 3943), Spring 2026 |
| `/computer-vision` | Computer Vision (CS-GY 6643), Fall 2026 |

The two course pages share `src/components/CoursePage.astro`. Course images,
schedules, and readings are passed in from each page's frontmatter.

## Data

| File | Purpose |
|---|---|
| `src/data/site.json` | Curated baseline: 82 publications, team, alumni, projects, funding objects, PI bio. 11 entries carry a per-entry `doi`, 6 carry an official `url`, 3 carry an award `note`. |
| `src/data/dois.json` | 72 DOI matches keyed by normalized title; per-entry `doi`/`url` fields in `site.json` win. |
| `src/data/nips.json` | 7 NeurIPS papers. Two 2026 papers are merged into `site.json`; the third is excluded. |
| `src/data/publications.config.json` | Locked refresh policy: strategy B, GitHub PR, monthly cron, preprint policy 1, exact DOI/title matching, excluded titles. |

Publication links resolve in this order: per-entry `url`, per-entry `doi`,
normalized-title lookup in `dois.json`. `10.52202/` (Curran Associates) is
blocked in favor of the official NeurIPS page.

Preprint policy is **1**: keep a preprint until a published version exists,
then remove the preprint row and show the published version. The 2024
*Alternative splicing* and 2019 *Neurocognitive and functional heterogeneity*
preprints were removed under this policy; their published versions remain.

Venue labels are rendered as a **short label plus year** (`Neuron 2026`,
`Nature Communications 2025`, `ICASSP 2023`). The full venue remains in the
row tooltip.

Six of the 82 entries have no link: conference abstracts, a dissertation, the
AABI Sinkhorn paper, and one medRxiv preprint without a confident DOI match.

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

`publications:apply` refuses to run if `site.json` changed after the review was
generated. It preserves team, alumni, projects, funding, and award notes.

Sources: OpenAlex (PI works), SerpApi/Google Scholar (discovery), NeurIPS
(`nips.json`), Europe PMC (bioRxiv/medRxiv preprints), and Crossref (exact-title
DOI refresh). Matching is exact DOI first, then exact normalized title. There
is no fuzzy title matching.

### Monthly GitHub Action

`.github/workflows/publications.yml` runs at `0 14 1 * *` (14:00 UTC on the
first of each month) and on `workflow_dispatch`. It:

1. Refreshes `nips.json`.
2. Builds the review diff.
3. Applies it to the `publications/monthly` branch.
4. Audits every publication link.
5. Builds the site and captures screenshots of the publication list.
6. Opens or updates a PR.

It does **not** auto-merge. Erdem Varol reviews the diff, screenshots, and DOI
audit, then approves and merges. Repository branch protection on `main` must
require that approval; the workflow cannot enforce reviewer identity.

**Do not run `scripts/sync-site-text.py`.** It rebuilds `site.json` from
`../_crawl`, writes `funding` as strings, and drops per-entry overrides, award
notes, and manual metadata fixes. It is a full-file overwrite, not a merge.

## Design tokens

All in `src/styles/global.css`, first block:

- Dark grey page `#101012`, ink `#f2f0eb`, violet accent `#b48cff`.
- Cardo for display type, Instrument Sans for body, Space Grotesk for labels and
  metadata.
- 1px rules, no radius, no shadows, no cards on a dark background.
- Animated line grid: 84px cells, 9s loop, disabled under reduce-motion.
- Root font scales `17px → 22px`; max content width 2400px at ≥2200px.
- Header collapses to the MENU button at ≤1280px.

The home page is built around compact publication rows and a 16:11 hero
carousel: five 4s, 1280×720, 24fps WebM loops with MP4 fallbacks, dots, arrows,
and a 7s auto-advance. Only the active video loads; the next is preloaded.
`prefers-reduced-motion` keeps the poster static.

## Adding content

**A project** — add the project to `src/data/site.json`; the page reads all 11
projects from that file. The unused `src/content/projects/*.md` files are a
first-pass experiment and are not rendered.

**A person** — drop a 4:5 JPEG in `public/img/team/` or `public/img/alumni/`,
add the entry to `src/data/site.json`, and add the image mapping in
`src/pages/index.astro`.

**A publication** — edit `src/data/site.json` directly. Add a per-entry `doi` or
`url` when the title-keyed lookup is wrong or a better official link exists.
Keep `note` short (Spotlight, Oral Presentation, Top 3% of papers). The monthly
pipeline will propose new papers for review; use
`src/data/publications.config.json` for titles that must never be imported.

## Passcode gate

The GitHub Pages build is **public**. The gate still exists for local previews:

```bash
# .env (gitignored)
PUBLIC_SITE_LOCKED=true
SITE_PASSWORD=<set this locally; never commit it>
```

`PUBLIC_SITE_LOCKED=false` builds plain pages. The password is never shipped —
only its SHA-256 — and unlocking lasts for the browser session.

**This is a deterrent, not real access control.** Static hosting serves the
whole HTML to anyone who asks; the gate only hides it in the browser. For real
protection put the site behind Cloudflare Access or Netlify password
protection.

## Deploy

GitHub Actions → Pages. The workflow builds with
`SITE_URL=https://pxndey.github.io` and `SITE_BASE=/neuroinfolab-demo` for the
project-page URL, and sets `PUBLIC_SITE_LOCKED=false`.

For a custom domain, set `SITE_URL=https://www.neuroinformaticslab.com` and
`SITE_BASE=/`, and add `public/CNAME` containing the domain before the first
deploy. DNS needs the four `185.199.108–111.153` A records plus
`www → pxndey.github.io`.

## Current gaps

- The monthly PR requires GitHub branch protection to enforce Erdem’s approval.
- `scripts/sync-site-text.py` is unsafe until its funding schema and overwrite
  behavior are fixed.
- Six publications remain unlinked (see Data above).
- The 2023 *Neuroimaging-AI Endophenotypes* medRxiv entry has no confident DOI
  match.
- Known defects: course-page nav active state, carousel pause, stale homepage
  dates, inconsistent course-term freshness, and the 2.8 MB eager-loaded CV GIF.
- The UI backlog is closed by user decision; do not reopen it.
- Scholar counters are not wired yet.

`HANDOFF.md` is the authoritative status file, including the locked decisions
and pipeline operations.
