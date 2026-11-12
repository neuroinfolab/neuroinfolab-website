export const base = import.meta.env.BASE_URL.replace(/\/$/, '');

/** Prefix a root-relative path with Astro's configured base ('' in dev, '/pxndey-site' on Pages). */
export const url = (path: string) => (path.startsWith('/') ? `${base}${path}` : path);
