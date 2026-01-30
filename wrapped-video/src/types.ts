// ============================================
// LEGACY GITHUB TYPES (for backward compatibility)
// ============================================

export type HeroStats = {
  prsMerged: number;
  linesAdded: number;
  linesRemoved: number;
  reviewsGiven: number;
  repositoriesContributed: number;
};

export type BigRock = {
  title: string;
  repo: string;
  impact: string;
  linesChanged: number;
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

// ============================================
// SLACK WRAPPED TYPES
// ============================================

export type ChannelStats = {
  totalMessages: number;
  totalWords: number;
  totalContributors: number;
  activeDays: number;
};

export type FunFact = {
  label: string;
  value: string | number;
  detail: string;
};

export type QuarterActivity = {
  quarter: string;
  messages: number;
  highlights: string[];
  // Legacy field for backward compatibility
  prs?: number;
};

export type TopContributor = {
  username: string;
  displayName: string;
  team: string;
  messageCount: number;
  contributionPercent: number;
  funTitle: string;
  funFact: string;
};

export type StatHighlight = {
  label: string;
  value: number;
  unit: string;
  context: string;
  trend?: string;
};

export type Record = {
  title: string;
  winner: string;
  value: number;
  unit: string;
  comparison: string;
  quip: string;
};

export type Competition = {
  category: string;
  participants: string[];
  scores: number[];
  winner: string;
  margin: string;
  quip: string;
};

export type Superlative = {
  title: string;
  winner: string;
  value: number;
  unit: string;
  percentile: string;
  quip: string;
};

export type Insights = {
  interesting: string[];
  funny: string[];
  stats: StatHighlight[];
  records: Record[];
  competitions: Competition[];
  superlatives: Superlative[];
  roasts: string[];
};

export type Meta = {
  channelName: string;
  year: number;
  generatedAt: string;
  // Legacy field for backward compatibility
  username?: string;
};

// ============================================
// CONTENT ANALYSIS TYPES (Two-Pass Analysis)
// ============================================

export type YearStory = {
  opening: string;
  arc: string;
  climax: string;
  closing: string;
};

export type TopicHighlight = {
  topic: string;
  insight: string;
  bestQuote: string;
  period: string;
};

export type Quote = {
  text: string;
  author: string;
  context: string;
  period: string;
};

export type PersonalityType = {
  username: string;
  displayName: string;
  personalityType: string;
  evidence: string;
  funFact: string;
};

export type ContentAnalysis = {
  yearStory: YearStory | null;
  topicHighlights: TopicHighlight[];
  bestQuotes: Quote[];
  personalityTypes: PersonalityType[];
};

// ============================================
// SLACK VIDEO DATA
// ============================================

export type SlackVideoData = {
  channelStats: ChannelStats;
  quarterlyActivity: QuarterActivity[];
  topContributors: TopContributor[];
  funFacts: FunFact[];
  insights: Insights;
  meta: Meta;
  contentAnalysis?: ContentAnalysis;
};

// ============================================
// LEGACY VIDEO DATA (GitHub)
// ============================================

export type VideoData = {
  heroStats: HeroStats;
  funFacts: FunFact[];
  bigRocks: BigRock[];
  quarterlyActivity: QuarterActivity[];
  topRepos: TopRepo[];
  yearInReview: YearInReview;
  meta: Meta;
};
