export const base = import.meta.env.BASE_URL.replace(/\/$/, '');

/** Prefix a root-relative path with Astro's configured base ('' in dev, '/neuroinfolab-demo' on Pages). */
export const url = (path: string) => (path.startsWith('/') ? `${base}${path}` : path);

/** Prefix root-relative href/src attributes inside crawled HTML rendered with set:html. */
export const withBase = (html: string) =>
  html.replace(/\b(href|src)="\/(?!\/)/g, `$1="${base}/`);
