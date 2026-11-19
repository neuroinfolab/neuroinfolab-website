import { parse } from 'smol-toml';

export interface CourseLink {
  label: string;
  href: string;
}

export interface CourseInfo {
  label: string;
  text: string;
  href?: string;
  links?: CourseLink[];
}

export interface CoursePerson {
  role: string;
  name: string;
  email?: string;
  office?: string;
  officeAfter?: string;
  image?: string;
  links?: CourseLink[];
}

export interface CourseRow {
  date: string;
  topic: string;
  materials?: CourseLink[];
  note?: string;
}

export interface ReadingGroup {
  title: string;
  items: Array<{ text: string; href?: string }>;
}

export interface CourseSection {
  title: string;
  paragraphs: string[];
  links?: CourseLink[];
  list?: string[];
}

export interface CourseImage {
  src: string;
  srcSmall?: string;
  webp?: string;
  webpSmall?: string;
  alt: string;
  caption?: string;
  creditHref?: string;
  tone?: 'light';
}

export interface CoursePageData {
  title: string;
  code: string;
  term: string;
  image?: CourseImage;
  intro: string[];
  info: CourseInfo[];
  team: CoursePerson[];
  sections?: CourseSection[];
  schedule: CourseRow[];
  readings: ReadingGroup[];
  previous?: CourseLink | CourseLink[];
  archiveNote?: string;
}

// Every course term lives in one TOML file, including the archived offerings.
const files = import.meta.glob('../data/courses/*.toml', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const courses = new Map(
  Object.entries(files).map(([path, raw]) => [
    path.split('/').pop()!.replace(/\.toml$/, ''),
    parse(raw) as unknown as CoursePageData,
  ]),
);

export function getCourse(slug: string): CoursePageData {
  const course = courses.get(slug);
  if (!course) {
    throw new Error(
      `No course data for "${slug}". Add src/data/courses/${slug}.toml.`,
    );
  }
  return course;
}
