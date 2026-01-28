export type HeroStats = {
  prsMerged: number;
  linesAdded: number;
  linesRemoved: number;
  reviewsGiven: number;
  repositoriesContributed: number;
};

export type FunFact = {
  label: string;
  value: string | number;
  detail: string;
};

export type BigRock = {
  title: string;
  repo: string;
  impact: string;
  linesChanged: number;
};

export type QuarterActivity = {
  quarter: string;
  prs: number;
  highlights: string;
};

export type TopRepo = {
  name: string;
  prs: number;
  funFact: string;
};

export type YearInReview = {
  headline: string;
  tagline: string;
};

export type Meta = {
  username: string;
  year: number;
  generatedAt: string;
};

export type VideoData = {
  heroStats: HeroStats;
  funFacts: FunFact[];
  bigRocks: BigRock[];
  quarterlyActivity: QuarterActivity[];
  topRepos: TopRepo[];
  yearInReview: YearInReview;
  meta: Meta;
};
