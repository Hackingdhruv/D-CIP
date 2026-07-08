import type { UserReadSlim } from './user';

export type CaseStatus =
  | 'draft'
  | 'open'
  | 'in_progress'
  | 'under_review'
  | 'on_hold'
  | 'closed'
  | 'archived';

export type CasePriority = 'low' | 'medium' | 'high' | 'critical';

export type AssignmentRole = 'investigator' | 'analyst' | 'supervisor';

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';

export type TaskPriority = 'low' | 'medium' | 'high';

export interface CaseAssignmentRead {
  user: UserReadSlim;
  role: AssignmentRole;
  assignedAt: string;
}

export interface CaseActivityRead {
  id: string;
  action: string;
  description: string;
  eventData: Record<string, unknown>;
  createdAt: string;
  actor: UserReadSlim | null;
}

export interface ChecklistItem {
  id: string;
  text: string;
  checked: boolean;
}

export interface CaseTaskRead {
  id: string;
  caseId: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  dueDate: string | null;
  checklist: ChecklistItem[];
  assignee: UserReadSlim | null;
  createdBy: UserReadSlim;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
}

export interface CaseNoteRead {
  id: string;
  caseId: string;
  title: string;
  content: string;
  isPinned: boolean;
  createdBy: UserReadSlim;
  updatedBy: UserReadSlim | null;
  createdAt: string;
  updatedAt: string;
}

export interface CaseRead {
  id: string;
  referenceNumber: string;
  title: string;
  description: string | null;
  status: CaseStatus;
  priority: CasePriority;
  category: string | null;
  tags: string[];
  isPrivate: boolean;
  isStarred: boolean;
  owner: UserReadSlim;
  createdBy: UserReadSlim;
  assignments: CaseAssignmentRead[];
  tasks: CaseTaskRead[];
  notes: CaseNoteRead[];
  taskCount: number;
  openTaskCount: number;
  noteCount: number;
  assignmentCount: number;
  createdAt: string;
  updatedAt: string;
  closedAt: string | null;
  archivedAt: string | null;
}

export interface CaseReadSlim {
  id: string;
  referenceNumber: string;
  title: string;
  description: string | null;
  status: CaseStatus;
  priority: CasePriority;
  category: string | null;
  tags: string[];
  isPrivate: boolean;
  isStarred: boolean;
  owner: UserReadSlim;
  taskCount: number;
  openTaskCount: number;
  noteCount: number;
  assignmentCount: number;
  createdAt: string;
  updatedAt: string;
  closedAt: string | null;
  archivedAt: string | null;
}

export interface CaseListResponse {
  items: CaseReadSlim[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface CaseImportPreview {
  title: string;
  description?: string;
  priority: CasePriority;
  category?: string;
  tags: string[];
  notes: string[];
  rawTextExcerpt: string;
  aiUsed: boolean;
}

export interface CaseCreate {
  title: string;
  description?: string;
  status?: CaseStatus;
  priority?: CasePriority;
  category?: string;
  tags?: string[];
  isPrivate?: boolean;
}

export interface CaseUpdate {
  title?: string;
  description?: string;
  status?: CaseStatus;
  priority?: CasePriority;
  category?: string;
  tags?: string[];
  isPrivate?: boolean;
  isStarred?: boolean;
}

export interface CaseAssignEntry {
  userId: string;
  role: AssignmentRole;
}

export interface CaseAssignRequest {
  assignments: CaseAssignEntry[];
}

export interface CaseTaskCreate {
  title: string;
  description?: string;
  priority?: TaskPriority;
  assigneeId?: string;
  dueDate?: string;
  checklist?: ChecklistItem[];
}

export interface CaseTaskUpdate {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assigneeId?: string;
  dueDate?: string;
  checklist?: ChecklistItem[];
}

export interface CaseNoteCreate {
  title: string;
  content?: string;
  isPinned?: boolean;
}

export interface CaseNoteUpdate {
  title?: string;
  content?: string;
  isPinned?: boolean;
}
