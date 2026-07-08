// Evidence domain types

export type EvidenceStatus =
  | 'uploaded'
  | 'hashing'
  | 'metadata_extraction'
  | 'ocr_queue'
  | 'ai_queue'
  | 'timeline_queue'
  | 'graph_queue'
  | 'indexed'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type EvidencePriority = 'low' | 'medium' | 'high' | 'critical';

export type CustodyAction =
  | 'uploaded'
  | 'viewed'
  | 'downloaded'
  | 'processed'
  | 'tagged'
  | 'updated'
  | 'linked'
  | 'exported'
  | 'verified'
  | 'deleted'
  | 'restored';

export interface EvidenceUploadedBy {
  id: string;
  fullName: string;
  email: string;
  username: string;
  avatarUrl: string | null;
}

export interface EvidenceReadSlim {
  id: string;
  caseId: string;
  originalFilename: string;
  fileSize: number;
  mimeType: string;
  fileExtension: string;
  sha256Hash: string;
  status: EvidenceStatus;
  tags: string[];
  priority: EvidencePriority;
  source: string | null;
  classification: string | null;
  isStarred: boolean;
  url: string;
  uploadedBy: EvidenceUploadedBy;
  createdAt: string;
  updatedAt: string;
}

export interface EvidenceRead extends EvidenceReadSlim {
  processingError: string | null;
  processingStartedAt: string | null;
  processingCompletedAt: string | null;
  extractedMetadata: Record<string, unknown>;
  notes: string | null;
  deletedAt: string | null;
}

export interface EvidenceUpdate {
  tags?: string[];
  priority?: EvidencePriority;
  source?: string;
  classification?: string;
  notes?: string;
  isStarred?: boolean;
}

export interface EvidenceListResponse {
  items: EvidenceReadSlim[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface EvidenceCustodyActor {
  id: string;
  fullName: string;
  email: string;
  username: string;
  avatarUrl: string | null;
}

export interface EvidenceCustodyEvent {
  id: string;
  evidenceId: string;
  action: CustodyAction;
  description: string;
  reason: string | null;
  eventData: Record<string, unknown>;
  actor: EvidenceCustodyActor | null;
  createdAt: string;
}

export interface EvidencePreviewResponse {
  type: 'text' | 'image' | 'pdf' | 'unavailable';
  content?: string;
  url?: string;
  truncated?: boolean;
  reason?: string;
}

export interface EvidenceVerifyResponse {
  matches: boolean;
  originalHash: string;
  computedHash: string;
}
