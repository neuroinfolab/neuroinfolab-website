# neuroinfolab-demo

The Neuroinformatics Lab site, rebuilt. Astro 7, static output, no backend, no runtime
dependencies. Content is Markdown/JSON plus a handful of `.astro` components.

Live preview: https://pxndey.github.io/neuroinfolab-demo/ (passcode gated).

```bash
pnpm install
pnpm dev        # http://localhost:4321
pnpm build      # -> dist/
pnpm preview    # serve dist/
```

## Pages

| Route | What it holds |
|---|---|
| `/` | Hero, PI, team strip, featured projects, latest papers, funding and join CTA |
| `/research` | All 11 projects with full descriptions and collaborator links |
| `/team` | PI bio, members, alumni, lab-life gallery |
| `/publications` | All 84 papers, 2025 back to 2016 & older, with year jump links |
| `/teaching` | Current and previous course offerings |
| `/teaching/<slug>` | Full course page: description, staff, schedule, lecture links, readings |
| `/join` | Ph.D., postdoc and current-NYU-student openings |
| `/404` | Not-found page |

The six course pages are ports of the old Squarespace pages:

```
/teaching/neuroinformatics-spring26   (Spring 2026)
/teaching/neuroinformatics-spring25   (Spring 2025)
/teaching/neuroinformatics-spring24   (Spring 2024)
/teaching/computer-vision-fall26      (Fall 2026)
/teaching/computer-vision-fall25      (Fall 2025)
/teaching/computer-vision-fall24      (Fall 2024)
```

Old Squarespace paths are not preserved. A small redirect map can be added at the host
if those links need to keep working.

## Layout

```
public/
  media/                 5 looping microscopy clips + posters
  img/team|alumni|life/  portraits and lab photos, 4:5
  docs/                  CV, project PDFs, syllabi, postdoc ad
src/
  data/site.json         PI bio, people, publications, projects, funding
  data/courses.json      parsed course pages (schedule + readings, links intact)
  data/lab.ts            shared accessors, link maps, PI bio HTML, course metadata
  data/images.ts         portrait and lab-life image maps
  content/projects/*.md  reserved for future project detail pages
  components/            Header, Footer, PageHead, ProjectCard, PubList
  layouts/Base.astro     <head>, fonts, gate, reveal + menu scripts
  pages/                 one file per route; teaching/[slug] builds the courses
  styles/global.css      tokens, reset, header/footer, shared components
  styles/pages/*.css     page-specific layout only
scripts/
  sync-site-text.py      crawl -> src/data/site.json
  sync-courses.py        crawl -> src/data/courses.json
  shots.mjs              playwright screenshots at desktop + phone
```

## Copy and data

Nothing is paraphrased. `scripts/sync-site-text.py` re-reads
`../_crawl/raw/home.html` and `projects.html` and writes `src/data/site.json`:
PI bio, team, alumni, publications (including `2016 & Older`), funding and projects.
`scripts/sync-courses.py` reads the six course HTML files and writes
`src/data/courses.json`, preserving links, schedule tables and essential reads.
Old `/s/*.pdf` links are rewritten to `/docs/*.pdf`; old course URLs are rewritten to
the new `/teaching/...` routes.

```bash
pnpm sync:site
pnpm sync:courses
```

Person links now come from the crawl (`site` field in `src/data/site.json`). Project
collaborator links and the PI's inline bio links live in `src/data/lab.ts`.
`src/content/projects/` and `ProjectTile.astro` are from the first one-page pass and
are not used by the current research page; it reads `site.json` so all 11 projects are
in one place.

## Adding content

**A person** — add the portrait to `public/img/team/` or `public/img/alumni/`, add the
entry to `src/data/site.json` (or re-run the crawler if the old site changed), and add
the image mapping to `src/data/images.ts`.

**A project** — edit the project entry in `src/data/site.json` (title, desc, collab,
poster) and add any new collaborator URL to `collaboratorLinks` in `src/data/lab.ts`.
Projects are numbered by their order in the JSON and get `#p-01`… anchors on
`/research`.

**A course** — add the crawled HTML to `_crawl/raw/`, add the file to `COURSES` in
`scripts/sync-courses.py`, add its metadata to `courseNotes` in `src/data/lab.ts`, and
run `pnpm sync:courses`.

**A paper** — update the publications section of the old site / crawl and run
`pnpm sync:site`, or edit `src/data/site.json` directly if the lab's own wording
changed. Google Scholar remains the source of truth.

## Design tokens and CSS

All shared values are in the first block of `src/styles/global.css`: `--bg`, `--ink`,
`--muted`, `--rule`, `--accent`, `--sans`, `--serif`, `--mono`, `--gutter`.

- Dark grey page `#1b1b1d`, ink `#edebe6`, violet `#b48cff` for links, year headers,
  role labels and in-text links.
- Instrument Serif for headings, Instrument Sans for body, JetBrains Mono for labels.
- 1px rules, no radius, no shadows; panels are flat against the dark background.
- Slowly drifting grid behind the hero (`.grid-bg`, 48s loop, disabled under
  reduce-motion).

`global.css` is the shared layer: tokens, reset, header/footer, gate, typography,
`.prose`, publication/people/PI styles. Page-only layouts are separate files under
`src/styles/pages/` (`home`, `research`, `team`, `publications`, `teaching`, `join`,
`404`) and are imported by the page that needs them. Change a colour, font or gutter
once in `global.css`; page files should only use the variables.

## Passcode gate

`.env` (gitignored):

```
PUBLIC_SITE_LOCKED=true
SITE_PASSWORD=***REMOVED***
```

`PUBLIC_SITE_LOCKED=false` builds plain pages. The password is never shipped — only its
SHA-256 — and unlocking lasts for the browser session.

**This is a deterrent, not real access control.** Static hosting serves the whole HTML
to anyone who asks; the gate only hides it in the browser. For real protection put the
site behind Cloudflare Access (free for up to 50 people) or Netlify password
protection.

## Deploy

GitHub Actions → Pages. The workflow builds with:

```
SITE_URL   https://pxndey.github.io
SITE_BASE  /neuroinfolab-demo
PUBLIC_SITE_LOCKED true
SITE_PASSWORD <secret>
```

Those defaults are for the project-page URL. For the custom domain, set repository
variables `SITE_URL=https://www.neuroinformaticslab.com` and `SITE_BASE=/`, and add
`public/CNAME` containing the domain before the first deploy. DNS needs the four
`185.199.108–111.153` A records plus `www → pxndey.github.io`.

Changing DNS does not affect email unless the whole zone is moved; if you move
nameservers to Cloudflare, recreate MX/SPF/DKIM/TXT records first.

## Still to do

- Google Scholar citation/h-index counters are not wired; the numbers are not shown.
- Old Squarespace course URLs 404 by design; add redirects if the links matter.
- Check the people list, roles and lab-life captions with the PI before the gate comes
  down.
- Project detail pages (the `src/content/projects` collection) are reserved but not
  built.
