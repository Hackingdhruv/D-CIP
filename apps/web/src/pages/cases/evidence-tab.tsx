import { useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  Eye,
  FileArchive,
  FileAudio,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileVideo,
  Fingerprint,
  Loader2,
  MoreHorizontal,
  RefreshCw,
  Search,
  Shield,
  ShieldCheck,
  Star,
  Trash2,
  Upload,
  X,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  useDeleteEvidence,
  useEvidence,
  useEvidenceCustody,
  useEvidencePreview,
  useUpdateEvidence,
  useUploadEvidence,
  useVerifyEvidence,
} from '@/hooks/use-evidence';
import { evidenceApi, type UploadProgress } from '@/lib/api/evidence';
import type { EvidenceReadSlim, EvidenceStatus } from '@/types/evidence';

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function shortHash(hash: string): string {
  return hash.slice(0, 8) + '…' + hash.slice(-4);
}

function FileTypeIcon({ mime, ext, className = 'h-5 w-5' }: { mime: string; ext: string; className?: string }) {
  if (mime.startsWith('image/')) return <FileImage className={className} />;
  if (mime.startsWith('video/')) return <FileVideo className={className} />;
  if (mime.startsWith('audio/')) return <FileAudio className={className} />;
  if (mime === 'application/pdf' || ext === 'pdf') return <FileText className={`${className} text-red-500`} />;
  if (['xlsx', 'csv'].includes(ext) || mime.includes('spreadsheet'))
    return <FileSpreadsheet className={`${className} text-green-600`} />;
  if (['zip', 'tar', 'gz', '7z'].includes(ext) || mime.includes('zip'))
    return <FileArchive className={`${className} text-amber-600`} />;
  if (['json', 'xml', 'html', 'log', 'txt'].includes(ext) || mime.startsWith('text/'))
    return <FileCode className={`${className} text-blue-500`} />;
  return <FileText className={className} />;
}

const STATUS_BADGE: Record<EvidenceStatus, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  uploaded: { label: 'Uploaded', variant: 'secondary' },
  hashing: { label: 'Hashing', variant: 'secondary' },
  metadata_extraction: { label: 'Processing', variant: 'secondary' },
  ocr_queue: { label: 'OCR Queue', variant: 'secondary' },
  ai_queue: { label: 'AI Queue', variant: 'secondary' },
  timeline_queue: { label: 'Timeline', variant: 'secondary' },
  graph_queue: { label: 'Graph', variant: 'secondary' },
  indexed: { label: 'Indexed', variant: 'default' },
  completed: { label: 'Ready', variant: 'default' },
  failed: { label: 'Failed', variant: 'destructive' },
  cancelled: { label: 'Cancelled', variant: 'outline' },
};

// ── Upload zone ────────────────────────────────────────────────────────────────

function UploadDrawer({
  caseId,
  open,
  onOpenChange,
}: {
  caseId: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const [queued, setQueued] = useState<File[]>([]);
  const [uploads, setUploads] = useState<UploadProgress[]>([]);
  const [done, setDone] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutateAsync, isPending } = useUploadEvidence(caseId);

  function addFiles(files: FileList | null) {
    if (!files) return;
    setQueued((prev) => [...prev, ...Array.from(files)]);
    setDone(false);
  }

  function removeQueued(i: number) {
    setQueued((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function handleUpload() {
    if (!queued.length) return;
    await mutateAsync({
      files: queued,
      onProgress: setUploads,
    });
    setDone(true);
    setQueued([]);
  }

  function handleClose() {
    setQueued([]);
    setUploads([]);
    setDone(false);
    onOpenChange(false);
  }

  const allDone = uploads.length > 0 && uploads.every((u) => u.status !== 'uploading');

  return (
    <Sheet open={open} onOpenChange={handleClose}>
      <SheetContent side="right" className="w-[440px] sm:w-[500px] flex flex-col">
        <SheetHeader>
          <SheetTitle>Upload Evidence</SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-4">
          {/* Drop zone */}
          {!isPending && !done && (
            <div
              className={`relative flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 transition-colors cursor-pointer ${
                dragOver
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/30 hover:border-primary/60'
              }`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                addFiles(e.dataTransfer.files);
              }}
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <div className="text-center">
                <p className="text-sm font-medium">Drop files here or click to browse</p>
                <p className="text-xs text-muted-foreground mt-1">
                  PDF, DOCX, XLSX, images, video, audio, ZIP, CSV, JSON and more · Max 500 MB each
                </p>
              </div>
              <input
                ref={inputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => addFiles(e.target.files)}
              />
            </div>
          )}

          {/* Queued files */}
          {queued.length > 0 && !isPending && !done && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {queued.length} file{queued.length !== 1 ? 's' : ''} queued
              </p>
              {queued.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-sm"
                >
                  <FileTypeIcon mime={f.type} ext={f.name.split('.').pop() ?? ''} className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="flex-1 truncate">{f.name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{formatBytes(f.size)}</span>
                  <button
                    onClick={() => removeQueued(i)}
                    className="shrink-0 text-muted-foreground hover:text-destructive"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Upload progress */}
          {uploads.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Upload progress
              </p>
              {uploads.map((u, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
                >
                  {u.status === 'uploading' && (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" />
                  )}
                  {u.status === 'done' && (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
                  )}
                  {u.status === 'duplicate' && (
                    <RefreshCw className="h-4 w-4 shrink-0 text-amber-500" />
                  )}
                  {u.status === 'error' && (
                    <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />
                  )}
                  {u.status === 'pending' && (
                    <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="flex-1 truncate">{u.file.name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {u.status === 'done' && 'Uploaded'}
                    {u.status === 'duplicate' && 'Already exists'}
                    {u.status === 'error' && (u.error || 'Failed')}
                    {u.status === 'uploading' && 'Uploading…'}
                    {u.status === 'pending' && 'Queued'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {done && allDone && (
            <div className="flex flex-col items-center gap-2 py-4 text-center">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
              <p className="text-sm font-medium">Upload complete</p>
              <p className="text-xs text-muted-foreground">
                {uploads.filter((u) => u.status === 'done').length} file(s) added to evidence
              </p>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="border-t pt-4 flex gap-2 justify-end">
          <Button variant="outline" onClick={handleClose}>
            {done ? 'Close' : 'Cancel'}
          </Button>
          {!done && (
            <Button
              onClick={handleUpload}
              disabled={queued.length === 0 || isPending}
            >
              {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Upload {queued.length > 0 ? `${queued.length} file${queued.length !== 1 ? 's' : ''}` : ''}
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ── Preview panel ──────────────────────────────────────────────────────────────

function PreviewPanel({
  caseId,
  evidence,
  onClose,
}: {
  caseId: string;
  evidence: EvidenceReadSlim;
  onClose: () => void;
}) {
  const { data: preview, isLoading: loadingPreview } = useEvidencePreview(caseId, evidence.id);
  const { data: custody } = useEvidenceCustody(caseId, evidence.id);
  const { mutate: verify, isPending: verifying, data: verifyResult } = useVerifyEvidence(caseId);
  const { mutate: update } = useUpdateEvidence(caseId);

  function toggleStar() {
    update({ evidenceId: evidence.id, data: { isStarred: !evidence.isStarred } });
  }

  return (
    <Sheet open onOpenChange={onClose}>
      <SheetContent side="right" className="w-[480px] sm:w-[540px] flex flex-col p-0">
        <div className="flex items-start justify-between gap-2 p-4 border-b">
          <div className="flex items-center gap-2 min-w-0">
            <FileTypeIcon mime={evidence.mimeType} ext={evidence.fileExtension} className="h-6 w-6 shrink-0" />
            <div className="min-w-0">
              <p className="font-medium text-sm leading-tight truncate">{evidence.originalFilename}</p>
              <p className="text-xs text-muted-foreground">{formatBytes(evidence.fileSize)}</p>
            </div>
          </div>
          <div className="flex shrink-0 gap-1">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={toggleStar}>
              <Star className={`h-4 w-4 ${evidence.isStarred ? 'fill-amber-400 text-amber-400' : ''}`} />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* Preview area */}
          <div className="border-b">
            {loadingPreview && (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            )}
            {preview?.type === 'image' && preview.url && (
              <img
                src={preview.url}
                alt={evidence.originalFilename}
                className="w-full max-h-64 object-contain bg-muted/20"
              />
            )}
            {preview?.type === 'text' && (
              <div className="bg-muted/30 p-3">
                <pre className="text-xs font-mono whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                  {preview.content}
                </pre>
                {preview.truncated && (
                  <p className="text-xs text-muted-foreground mt-2 italic">
                    Showing first 8 KB — download for full content
                  </p>
                )}
              </div>
            )}
            {preview?.type === 'pdf' && (
              <div className="flex flex-col items-center justify-center h-32 gap-2 text-muted-foreground">
                <FileText className="h-8 w-8" />
                <p className="text-sm">PDF — open in browser to view</p>
                <a
                  href={preview.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs underline text-primary"
                >
                  Open PDF
                </a>
              </div>
            )}
            {preview?.type === 'unavailable' && (
              <div className="flex flex-col items-center justify-center h-28 gap-1.5 text-muted-foreground">
                <Eye className="h-6 w-6" />
                <p className="text-xs">{preview.reason}</p>
              </div>
            )}
          </div>

          {/* Properties */}
          <div className="p-4 space-y-4">
            <section>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                File Properties
              </p>
              <dl className="space-y-1.5 text-sm">
                {[
                  ['Type', evidence.mimeType],
                  ['Extension', evidence.fileExtension.toUpperCase() || '—'],
                  ['Size', formatBytes(evidence.fileSize)],
                  ['Uploaded', formatDate(evidence.createdAt)],
                  ['By', evidence.uploadedBy.fullName],
                  ['Status', STATUS_BADGE[evidence.status]?.label ?? evidence.status],
                ].map(([k, v]) => (
                  <div key={k as string} className="flex gap-2">
                    <dt className="w-20 shrink-0 text-muted-foreground">{k}</dt>
                    <dd className="truncate">{v as string}</dd>
                  </div>
                ))}
              </dl>
            </section>

            {/* Hash & integrity */}
            <section>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Integrity
              </p>
              <div className="rounded-md border bg-muted/30 px-3 py-2 text-xs font-mono break-all">
                {evidence.sha256Hash}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  disabled={verifying}
                  onClick={() => verify(evidence.id)}
                >
                  {verifying ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : (
                    <Fingerprint className="mr-1 h-3 w-3" />
                  )}
                  Verify hash
                </Button>
                {verifyResult && (
                  <span className={`flex items-center gap-1 text-xs ${verifyResult.matches ? 'text-green-600' : 'text-destructive'}`}>
                    {verifyResult.matches ? (
                      <><ShieldCheck className="h-3 w-3" /> Verified</>
                    ) : (
                      <><Shield className="h-3 w-3" /> Hash mismatch!</>
                    )}
                  </span>
                )}
              </div>
            </section>

            {/* Tags */}
            {evidence.tags.length > 0 && (
              <section>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Tags
                </p>
                <div className="flex flex-wrap gap-1">
                  {evidence.tags.map((t) => (
                    <Badge key={t} variant="secondary" className="text-xs">
                      {t}
                    </Badge>
                  ))}
                </div>
              </section>
            )}

            {/* Chain of custody */}
            {custody && custody.length > 0 && (
              <section>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Chain of Custody
                </p>
                <div className="space-y-2">
                  {custody.map((ev) => (
                    <div key={ev.id} className="flex gap-2 text-xs">
                      <span className="shrink-0 text-muted-foreground w-20 truncate">
                        {formatDate(ev.createdAt)}
                      </span>
                      <span className="shrink-0 font-medium capitalize">{ev.action}</span>
                      <span className="text-muted-foreground truncate">{ev.actor?.fullName ?? 'System'}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        </div>

        {/* Footer actions */}
        <div className="border-t p-3 flex gap-2">
          <a
            href={evidenceApi.downloadUrl(caseId, evidence.id)}
            download={evidence.originalFilename}
            className="flex-1"
          >
            <Button variant="outline" size="sm" className="w-full">
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Download
            </Button>
          </a>
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ── Evidence row ───────────────────────────────────────────────────────────────

function EvidenceRow({
  ev,
  caseId,
  onSelect,
}: {
  ev: EvidenceReadSlim;
  caseId: string;
  onSelect: (ev: EvidenceReadSlim) => void;
}) {
  const { mutate: del, isPending: deleting } = useDeleteEvidence(caseId);
  const { mutate: update } = useUpdateEvidence(caseId);
  const badge = STATUS_BADGE[ev.status] ?? { label: ev.status, variant: 'secondary' as const };

  return (
    <tr
      className="group border-b transition-colors hover:bg-accent/30 cursor-pointer"
      onClick={() => onSelect(ev)}
    >
      <td className="py-2.5 px-3">
        <FileTypeIcon mime={ev.mimeType} ext={ev.fileExtension} className="h-5 w-5 text-muted-foreground" />
      </td>
      <td className="py-2.5 pr-3 max-w-[220px]">
        <p className="text-sm font-medium truncate">{ev.originalFilename}</p>
        <p className="text-xs text-muted-foreground font-mono">{shortHash(ev.sha256Hash)}</p>
      </td>
      <td className="py-2.5 pr-3 text-sm text-muted-foreground whitespace-nowrap">
        {formatBytes(ev.fileSize)}
      </td>
      <td className="py-2.5 pr-3">
        <Badge variant={badge.variant} className="text-xs">
          {badge.label}
        </Badge>
      </td>
      <td className="py-2.5 pr-3 text-xs text-muted-foreground whitespace-nowrap">
        {ev.uploadedBy.fullName}
      </td>
      <td className="py-2.5 pr-3 text-xs text-muted-foreground whitespace-nowrap">
        {formatDate(ev.createdAt)}
      </td>
      <td className="py-2.5 pr-2" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 opacity-0 group-hover:opacity-100"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onSelect(ev)}>
              <Eye className="mr-2 h-4 w-4" />
              Preview
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <a
                href={evidenceApi.downloadUrl(caseId, ev.id)}
                download={ev.originalFilename}
                onClick={(e) => e.stopPropagation()}
              >
                <Download className="mr-2 h-4 w-4" />
                Download
              </a>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() =>
                update({ evidenceId: ev.id, data: { isStarred: !ev.isStarred } })
              }
            >
              <Star className={`mr-2 h-4 w-4 ${ev.isStarred ? 'fill-amber-400 text-amber-400' : ''}`} />
              {ev.isStarred ? 'Unstar' : 'Star'}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              disabled={deleting}
              onClick={() => del(ev.id)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

// ── Main EvidenceTab ───────────────────────────────────────────────────────────

export function EvidenceTab({ caseId }: { caseId: string }) {
  const [search, setSearch] = useState('');
  const [mimeFilter, setMimeFilter] = useState('');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selected, setSelected] = useState<EvidenceReadSlim | null>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useEvidence(caseId, {
    q: search || undefined,
    mimeCategory: mimeFilter || undefined,
    page,
    pageSize: 50,
  });

  const MIME_FILTERS = [
    { label: 'All types', value: '' },
    { label: 'Documents', value: 'application' },
    { label: 'Images', value: 'image' },
    { label: 'Video', value: 'video' },
    { label: 'Audio', value: 'audio' },
    { label: 'Text', value: 'text' },
  ];

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search evidence…"
            className="pl-9"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>

        <div className="flex items-center gap-2">
          {MIME_FILTERS.map((f) => (
            <Button
              key={f.value}
              size="sm"
              variant={mimeFilter === f.value ? 'default' : 'outline'}
              onClick={() => { setMimeFilter(f.value); setPage(1); }}
            >
              {f.label}
            </Button>
          ))}
        </div>

        <div className="ml-auto">
          <Button size="sm" onClick={() => setUploadOpen(true)}>
            <Upload className="mr-1.5 h-4 w-4" />
            Upload files
          </Button>
        </div>
      </div>

      {/* Stats */}
      {data && (
        <p className="text-sm text-muted-foreground">
          <span className="font-semibold text-foreground">{data.total}</span>{' '}
          evidence item{data.total !== 1 ? 's' : ''}
        </p>
      )}

      {/* Loading skeletons */}
      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Failed to load evidence. Please try again.
        </div>
      )}

      {/* Evidence table */}
      {!isLoading && !isError && data && (
        <>
          {data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed py-16 text-center">
              <Upload className="h-8 w-8 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">No evidence yet</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {search
                    ? `No results for "${search}"`
                    : 'Upload files to start building the evidence record.'}
                </p>
              </div>
              {!search && (
                <Button size="sm" onClick={() => setUploadOpen(true)}>
                  <Upload className="mr-1.5 h-4 w-4" />
                  Upload evidence
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50 text-xs font-medium text-muted-foreground">
                    <th className="py-2.5 px-3 text-left w-8" />
                    <th className="py-2.5 pr-3 text-left">Filename</th>
                    <th className="py-2.5 pr-3 text-left whitespace-nowrap">Size</th>
                    <th className="py-2.5 pr-3 text-left">Status</th>
                    <th className="py-2.5 pr-3 text-left">Uploaded by</th>
                    <th className="py-2.5 pr-3 text-left whitespace-nowrap">Date</th>
                    <th className="py-2.5 pr-2 w-8" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((ev) => (
                    <EvidenceRow
                      key={ev.id}
                      ev={ev}
                      caseId={caseId}
                      onSelect={setSelected}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {data.pages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page === data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {/* Upload drawer */}
      <UploadDrawer
        caseId={caseId}
        open={uploadOpen}
        onOpenChange={setUploadOpen}
      />

      {/* Preview panel */}
      {selected && (
        <PreviewPanel
          caseId={caseId}
          evidence={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
