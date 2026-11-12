import siteData from './site.json';
import courseData from './courses.json';

export const site = siteData;

export const LAB_NAME = 'Neuroinformatics Lab';

export const SCHOLAR = 'https://scholar.google.com/citations?user=7GlElV0AAAAJ';
export const YOUTUBE = 'https://www.youtube.com/channel/UC6aMrgW4-StJVg9YwUF0AiQ';
export const TWITTER = 'https://twitter.com/erdem___varol';
export const EMAIL = 'ev2240@nyu.edu';
export const ADDRESS = '370 Jay Street, Rooms 1158 (office) and 1166 (lab), Brooklyn, NY 11201';

/** External links that appear in the lab's own copy. */
export const links = {
  department: 'https://engineering.nyu.edu/academics/departments/computer-science-and-engineering',
  tandon: 'https://engineering.nyu.edu/',
  nyu: 'https://www.nyu.edu/',
  vida: 'https://vida.engineering.nyu.edu',
  columbiaStats: 'https://stat.columbia.edu/',
  zuckerman: 'https://zuckermaninstitute.columbia.edu/',
  columbia: 'https://www.columbia.edu/',
  paninski: 'http://www.stat.columbia.edu/~liam/',
  pennEse: 'https://www.ese.upenn.edu/',
  penn: 'https://www.upenn.edu/',
  davatzikos: 'https://www.med.upenn.edu/apps/faculty/index.php/g275/p32990',
  wharton: 'https://www.wharton.upenn.edu/',
  k99: 'https://reporter.nih.gov/search/5NKlWhoBEUav-buDakkgCw/project-details/10525865',
  bassets: 'https://www.instagram.com/thebassetsherlock',
  phdAdmissions: 'https://cs.nyu.edu/dynamic/phd/admissions/',
  interestForm: 'https://forms.gle/BrtJcpdfhE7TJSoQ9',
  cv: '/docs/varol_cv_1122.pdf',
  projectSummary: '/docs/NYU_Neuroinformatics_lab_summary.pdf',
  labPrimer: '/docs/neuroinformatics_lab_primer.pdf',
  postdocAd: '/docs/nyu_utsw_postdoc_ad.pdf',
};

/** PI bio, with the links the old site had. */
export const piBio = `
  <p>I’m an assistant professor at the <a href="${links.department}" target="_blank" rel="noopener">Department of Computer Science &amp; Engineering</a>
  at the <a href="${links.tandon}" target="_blank" rel="noopener">Tandon School of Engineering</a>,
  <a href="${links.nyu}" target="_blank" rel="noopener">NYU</a>. I’m also a part of the
  <a href="${links.vida}" target="_blank" rel="noopener">VIDA center</a>. Previously, I was a postdoc at the
  <a href="${links.columbiaStats}" target="_blank" rel="noopener">Department of Statistics</a>,
  <a href="${links.zuckerman}" target="_blank" rel="noopener">Zuckerman Institute</a>,
  <a href="${links.columbia}" target="_blank" rel="noopener">Columbia University</a> with
  <a href="${links.paninski}" target="_blank" rel="noopener">Liam Paninski</a>. Before that, I did my Ph.D. at the
  <a href="${links.pennEse}" target="_blank" rel="noopener">Department of Electrical &amp; Systems Engineering</a>
  at the <a href="${links.penn}" target="_blank" rel="noopener">University of Pennsylvania</a> under
  <a href="${links.davatzikos}" target="_blank" rel="noopener">Christos Davatzikos</a>. Whilst at Penn, I also received
  an A.M degree in Statistics from the <a href="${links.wharton}" target="_blank" rel="noopener">Wharton School</a>.
  I recently received the <a href="${links.k99}" target="_blank" rel="noopener">NIH/NIMH K99/R00 award</a> in 2022.
  I’m originally from Ankara, Turkey and grew up in New York City. I have two
  <a href="${links.bassets}" target="_blank" rel="noopener">basset hounds</a>.</p>
`;

/** Project collaborators who have a page on the old site. */
const collaboratorLinks: Record<string, string> = {
  'Junhao Wen': 'https://www.junhaowen.com/',
  'Christos Davatzikos': 'https://www.med.upenn.edu/cbica/christos/',
  'Richard Mann': 'https://mannlab.zuckermaninstitute.columbia.edu/',
  'Losonczy Lab': 'https://www.losonczylab.org/',
  'Arman Afrasiyabi': 'https://armanafrasiyabi.github.io/',
  'Alexis Weinreb': 'https://medicine.yale.edu/profile/alexis-weinreb/',
  'Sandeep Wontakal': 'https://scholar.google.com/citations?user=jpv7onYAAAAJ&hl=en',
  'Buzsaki Lab': 'https://buzsakilab.com/wp/',
  'Cole Hurwitz': 'https://colehurwitz.github.io/',
};

export const collaboratorUrl = (name: string): string => {
  if (collaboratorLinks[name]) return collaboratorLinks[name];
  const key = Object.keys(collaboratorLinks).find((k) => name.startsWith(k));
  return key ? collaboratorLinks[key] : '';
};

export const projects = site.projects.map((p, i) => {
  const index = String(i + 1).padStart(2, '0');
  return {
    ...p,
    index,
    anchor: `p-${index}`,
    href: `/research#p-${index}`,
    collabLinks: p.collab.map((name) => ({ name, href: collaboratorUrl(name) })),
  };
});

export const featuredProjects = projects.filter((p) => p.poster);

const shortSummaries: Record<string, string> = {
  'Multimodal registration': 'The same neurons in living and cleared tissue.',
  'Spatiotemporal Integration': 'How gene expression shapes connectivity.',
  'Connectivity and coactivity': 'Does what a neuron does reveal what it is?',
  'Whole-brain single-cell': 'Every neuron tracked in a moving worm.',
};

export const shortSummary = (title: string) =>
  Object.entries(shortSummaries).find(([key]) => title.startsWith(key))?.[1] ?? title;

/** Publications, newest year first, with the lab's own name highlighted. */
export const publicationYears = [...new Set(site.publications.map((p) => p.year))];

export const publicationsByYear = publicationYears.map((year) => ({
  year,
  items: site.publications.filter((p) => p.year === year),
}));

const escapeHtml = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export const formatAuthors = (authors: string) =>
  escapeHtml(authors).replace(/\bE Varol\b/g, '<span class="me">E Varol</span>');

export interface Course {
  slug: string;
  legacy: string;
  label: string;
  title: string;
  term: string;
  code: string;
  description: string;
  when: string;
  where: string;
  current: boolean;
  summary: string[];
  overview: string[];
  schedule: { headers: string[]; rows: string[][] };
  reads: string[];
  syllabus: string;
  previous: string;
}

const courseNotes: Record<string, { code: string; description: string; when: string; where: string; current: boolean }> = {
  'neuroinformatics-spring26': {
    code: 'CS-GY 9223 / CS-UY 3943',
    description:
      'A Ph.D.-level topics course on modeling, signal processing and data management for neuroscience, graded through journal club and four Kaggle competitions.',
    when: 'Tuesdays 2–4:30 pm',
    where: '2 MetroTech Center, Room 817',
    current: true,
  },
  'neuroinformatics-spring25': {
    code: 'CS-GY 9223 / CS-UY 3943',
    description:
      'A Ph.D.-level topics course on modeling, signal processing and data management for neuroscience, graded through journal club and four Kaggle competitions.',
    when: 'Tuesdays 2–4:30 pm',
    where: '2 MetroTech Center, Room 817',
    current: false,
  },
  'neuroinformatics-spring24': {
    code: 'CS-GY 9223 / CS-UY 3943',
    description:
      'A Ph.D.-level topics course on modeling, signal processing and data management for neuroscience, graded through a midterm project and Kaggle competitions.',
    when: 'Tuesdays 2–4:30 pm',
    where: '2 MetroTech Center, Room 817',
    current: false,
  },
  'computer-vision-fall26': {
    code: 'CS-GY 6643',
    description:
      'Graduate computer vision, from image formation and feature matching to transformers and Gaussian splatting, with a midterm and programming projects.',
    when: 'Thursdays 11 am–1:30 pm',
    where: '6 MetroTech Center, Room 475',
    current: true,
  },
  'computer-vision-fall25': {
    code: 'CS-GY 6643',
    description:
      'Graduate image processing and computer vision, from filtering and feature matching to neural networks and vision transformers.',
    when: 'Thursdays 11 am–1:30 pm',
    where: '6 MetroTech Center, Room 475',
    current: false,
  },
  'computer-vision-fall24': {
    code: 'CS-GY 6643',
    description:
      'Graduate image processing and computer vision, from filtering and feature matching to neural networks and vision transformers.',
    when: 'Thursdays 11 am–1:30 pm',
    where: '6 MetroTech Center, Room 475',
    current: false,
  },
};

export const courses: Course[] = Object.entries(courseData).map(([slug, c]) => ({
  ...c,
  ...courseNotes[slug],
  slug,
}));

export const currentCourses = courses.filter((c) => c.current);
export const pastCourses = courses.filter((c) => !c.current);
