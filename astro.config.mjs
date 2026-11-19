import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// GitHub Pages serves project sites from /<repo>/, so the base has to be set at
// build time. Locally, and once a custom domain is attached, it stays '/'.
const site = process.env.SITE_URL ?? 'https://neuroinformaticslab.com';
const base = process.env.SITE_BASE ?? '/';

export default defineConfig({
  site,
  base,
  integrations: [sitemap()],
  compressHTML: 'jsx',
  build: {
    inlineStylesheets: 'auto',
  },
  prefetch: {
    prefetchAll: true,
  },
});
