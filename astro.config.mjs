import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// GitHub Pages serves project sites from /<repo>/, so the base has to be set at
// build time. Locally, and once a custom domain is attached, it stays '/'.
const site = process.env.SITE_URL ?? 'https://neuroinformaticslab.com';
const base = process.env.SITE_BASE ?? '/';

// Short links served as static redirect pages. GitHub Pages cannot send real
// 3xx headers, so Astro emits an HTML page with a meta refresh.
const redirects = {
  '/merscopeRegistration': {
    status: 301,
    destination: 'https://invivo-exvivo-cell-registration.vercel.app',
  },
  '/spikeLocalization': {
    status: 301,
    destination: 'https://sln-depth-raster-explorers.vercel.app/',
  },
  '/lfpformer': {
    status: 301,
    destination: 'https://lfpformer-nyu.vercel.app/',
  },
  '/macroToMicro': {
    status: 301,
    destination:
      'https://docs.google.com/presentation/d/1e-ioqVH0Zlbyw_zGOZCENiuqUrOXSCr0dB14Y8sgKcY/edit?usp=sharing',
  },
  '/lfp2gene': {
    status: 301,
    destination: 'https://lawrencelu0904.github.io/Lfp2Gene-page/',
  },
  '/midterms2026': {
    status: 301,
    destination: 'https://lawrencelu0904.github.io/kalshi_midterm_prediction/',
  },
};

export default defineConfig({
  site,
  base,
  redirects,
  integrations: [sitemap()],
  compressHTML: 'jsx',
  build: {
    inlineStylesheets: 'auto',
  },
  prefetch: {
    prefetchAll: true,
  },
});
