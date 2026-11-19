export const base = import.meta.env.BASE_URL.replace(/\/$/, '');


export const url = (path: string) => (path.startsWith('/') ? `${base}${path}` : path);
