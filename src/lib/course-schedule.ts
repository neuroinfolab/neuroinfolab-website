import { parse } from 'smol-toml';

export interface CourseMaterial {
  label: string;
  href?: string;
}

export interface CourseRow {
  date: string;
  topic: string;
  materials?: CourseMaterial[];
  note?: string;
}

// One TOML file per course offering, archives included. Only the schedule is
// stored here; the rest of each course page stays in its .astro frontmatter.
const files = import.meta.glob('../data/course-schedules/*.toml', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const schedules = new Map(
  Object.entries(files).map(([path, raw]) => {
    const slug = path.split('/').pop()!.replace(/\.toml$/, '');
    const data = parse(raw) as { schedule?: CourseRow[] };
    if (!Array.isArray(data.schedule)) {
      throw new Error(`No [[schedule]] rows in ${path}`);
    }
    return [slug, data.schedule];
  }),
);

export function getSchedule(slug: string): CourseRow[] {
  const schedule = schedules.get(slug);
  if (!schedule) {
    throw new Error(
      `No course schedule for "${slug}". Add src/data/course-schedules/${slug}.toml.`,
    );
  }
  return schedule;
}
