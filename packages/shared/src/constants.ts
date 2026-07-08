/** Sections that make up a case workspace (the core philosophy of D-CIP). */
export const CASE_WORKSPACE_SECTIONS = [
  'overview',
  'evidence',
  'timeline',
  'graph',
  'entities',
  'tasks',
  'notes',
  'ai-findings',
  'reports',
  'activity',
  'audit',
] as const;

export type CaseWorkspaceSection = (typeof CASE_WORKSPACE_SECTIONS)[number];

/** Review states for any AI-produced artifact. AI is always reviewable. */
export const AI_REVIEW_STATES = ['suggested', 'accepted', 'rejected', 'edited'] as const;
export type AiReviewState = (typeof AI_REVIEW_STATES)[number];

export const DEFAULT_PAGE_SIZE = 25;
export const MAX_PAGE_SIZE = 100;
