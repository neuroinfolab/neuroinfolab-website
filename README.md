# pxndey-site

The Neuroinformatics Lab site, rebuilt. Astro 7, static output, no backend, no runtime
dependencies. Everything is Markdown plus a handful of `.astro` components.

```bash
pnpm install
pnpm dev        # http://localhost:4321
pnpm build      # -> dist/
pnpm preview    # serve dist/
```

## Layout

```
public/
  media/          5 looping microscopy clips + posters (the visual material)
  img/team|alumni|life/   portraits and lab photos, 4:5
src/
  content/projects/*.md    one file per research project (frontmatter + prose)
  content.config.ts        Zod schema for each collection
  components/              Header, Footer, ProjectTile
  layouts/Base.astro       <head>, fonts, reveal + menu scripts
  pages/index.astro        hero, PI, team, alumni, projects, funding
  pages/publications.astro every paper, grouped by year
  styles/global.css        the whole design system
scripts/
  shots.mjs        playwright screenshots at desktop + phone
```

## Copy

Every word on the page comes from www.neuroinformaticslab.com. `scripts/sync-site-text.py`
re-reads `../_crawl/raw/*.html` and writes `src/data/site.json` (PI bio, team, alumni,
publications, projects). Nothing is paraphrased — edit the site JSON only if the lab's own
wording changes.

```bash
python3 scripts/sync-site-text.py   # after re-crawling the old site
```

## Adding content

**A project** — add `src/content/projects/name.md`:

```md
---
index: "06"
title: "…"
summary: "One sentence shown on the landing tile."
collab: ["Losonczy Lab"]
video: "/media/volume.mp4"
poster: "/media/volume.jpg"
tag: "circuit"
span: "normal"      # wide | tall | normal
order: 6
---

Body text for the project page.
```

**A person** — drop a 4:5 JPEG in `public/img/team/` and add the entry to the `people`
array in `src/pages/index.astro` (until the people collection lands).

## Design tokens

All in `src/styles/global.css`, first block: `--bg`, `--ink`, `--muted`, `--rule`,
`--accent`, `--sans`, `--serif`, `--mono`, `--gutter`.

- Dark grey page `#1b1b1d`, ink `#edebe6`, violet `#b48cff` for links, year headers and
  role labels.
- Instrument Serif for headings, Instrument Sans for body, JetBrains Mono for small labels.
- 1px rules, no radius, no shadows, no cards on a dark background.
- Slowly drifting grid behind the hero (`.grid-bg`, 48s loop, disabled under reduce-motion).

## Passcode gate

`.env` (gitignored):

```
PUBLIC_SITE_LOCKED=true
SITE_PASSWORD=***REMOVED***
```

`PUBLIC_SITE_LOCKED=false` builds plain pages. The password is never shipped — only its
SHA-256 — and unlocking lasts for the browser session.

**This is a deterrent, not real access control.** Static hosting serves the whole HTML to
anyone who asks; the gate only hides it in the browser. For real protection put the site
behind Cloudflare Access (free for up to 50 people) or Netlify password protection.

## Deploy

GitHub Actions → Pages. `public/CNAME` must contain the custom domain before the first
deploy, and DNS needs the four `185.199.108–111.153` A records plus
`www → pxndey.github.io`. See the root `_crawl/README.md` for the full checklist.

Publications and the Scholar counters are not wired yet; `src/pages/index.astro` has the
numbers hardcoded under a `// Placeholder` comment.
