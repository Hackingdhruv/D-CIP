import { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Archive,
  ChevronRight,
  Clock,
  FileUp,
  FolderKanban,
  ListTodo,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Star,
  StickyNote,
  Upload,
  Users,
} from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useHasPermission } from '@/contexts/auth-context';
import { PageHeader } from '@/components/common/page-header';
import { EmptyState } from '@/components/common/empty-state';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { useCases, useCreateCase, useImportCasePreview, useStarCase, useUnstarCase } from '@/hooks/use-cases';
import type { CaseImportPreview, CaseReadSlim, CasePriority, CaseStatus } from '@/types/case';

// ── Helpers ────────────────────────────────────────────────────────────────────

const STATUS_LABEL: Record<CaseStatus, string> = {
  draft: 'Draft',
  open: 'Open',
  in_progress: 'In Progress',
  under_review: 'Under Review',
  on_hold: 'On Hold',
  closed: 'Closed',
  archived: 'Archived',
};

const STATUS_VARIANT: Record<
  CaseStatus,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  draft: 'outline',
  open: 'default',
  in_progress: 'default',
  under_review: 'secondary',
  on_hold: 'outline',
  closed: 'secondary',
  archived: 'outline',
};

const PRIORITY_LABEL: Record<CasePriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

const PRIORITY_COLOR: Record<CasePriority, string> = {
  low: 'text-slate-500',
  medium: 'text-amber-600',
  high: 'text-orange-600',
  critical: 'text-red-600',
};

function formatRelative(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── Create Case Form ──────────────────────────────────────────────────────────

const createSchema = z.object({
  title: z.string().min(1, 'Title is required').max(500),
  description: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  category: z.string().optional(),
  isPrivate: z.boolean(),
});

type CreateFormValues = z.infer<typeof createSchema>;

function CreateCaseDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const navigate = useNavigate();
  const { mutateAsync, isPending } = useCreateCase();

  const form = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      title: '',
      description: '',
      priority: 'medium',
      category: '',
      isPrivate: false,
    },
  });

  async function onSubmit(values: CreateFormValues) {
    const created = await mutateAsync({
      title: values.title,
      description: values.description || undefined,
      priority: values.priority,
      category: values.category || undefined,
      isPrivate: values.isPrivate,
    });
    form.reset();
    onOpenChange(false);
    navigate(`/cases/${created.id}`);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New Investigation Case</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input placeholder="Brief case title…" autoFocus {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <textarea
                      className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
                      placeholder="What is this case about?"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="priority"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Priority</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="category"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Fraud, Cybercrime…" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="isPrivate"
              render={({ field }) => (
                <FormItem className="flex items-center gap-2.5 space-y-0 rounded-md border p-3">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div>
                    <FormLabel className="cursor-pointer">Private case</FormLabel>
                    <p className="text-xs text-muted-foreground">
                      Only visible to you and assigned team members.
                    </p>
                  </div>
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create case
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

// ── Import Case Dialog ────────────────────────────────────────────────────────

const ACCEPTED_TYPES = '.pdf,.docx,.doc,.txt,.csv,.json,.xlsx,.xls,.eml,.msg,.log,.md';

const importReviewSchema = z.object({
  title: z.string().min(1, 'Title is required').max(500),
  description: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  category: z.string().optional(),
  isPrivate: z.boolean(),
});
type ImportReviewValues = z.infer<typeof importReviewSchema>;

function ImportCaseDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<'upload' | 'parsing' | 'review'>('upload');
  const [preview, setPreview] = useState<CaseImportPreview | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const { mutateAsync: parseFile } = useImportCasePreview();
  const { mutateAsync: createCase, isPending: isCreating } = useCreateCase();

  const form = useForm<ImportReviewValues>({
    resolver: zodResolver(importReviewSchema),
    defaultValues: { title: '', description: '', priority: 'medium', category: '', isPrivate: false },
  });

  function resetDialog() {
    setStep('upload');
    setPreview(null);
    form.reset();
  }

  function handleOpenChange(v: boolean) {
    if (!v) resetDialog();
    onOpenChange(v);
  }

  async function processFile(file: File) {
    setStep('parsing');
    try {
      const data = await parseFile(file);
      setPreview(data);
      form.reset({
        title: data.title,
        description: data.description ?? '',
        priority: data.priority,
        category: data.category ?? '',
        isPrivate: false,
      });
      setStep('review');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to parse file');
      setStep('upload');
    }
  }

  function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    e.target.value = '';
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  }

  async function onSubmit(values: ImportReviewValues) {
    const created = await createCase({
      title: values.title,
      description: values.description || undefined,
      priority: values.priority,
      category: values.category || undefined,
      isPrivate: values.isPrivate,
    });
    handleOpenChange(false);
    navigate(`/cases/${created.id}`);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {step === 'upload' && (
          <>
            <DialogHeader>
              <DialogTitle>Import case from file</DialogTitle>
              <DialogDescription>
                Upload a document and AI will extract case details for you to review.
              </DialogDescription>
            </DialogHeader>

            <div
              className={`mt-2 flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 transition-colors cursor-pointer ${
                dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-10 w-10 text-muted-foreground" />
              <div className="text-center">
                <p className="text-sm font-medium">Drop a file here or click to browse</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  PDF, DOCX, TXT, CSV, JSON, XLSX, EML — up to 20 MB
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_TYPES}
                className="hidden"
                onChange={onFilePicked}
              />
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => handleOpenChange(false)}>Cancel</Button>
            </DialogFooter>
          </>
        )}

        {step === 'parsing' && (
          <>
            <DialogHeader>
              <DialogTitle>Analyzing document…</DialogTitle>
            </DialogHeader>
            <div className="flex flex-col items-center gap-4 py-10">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Extracting case details with AI</p>
            </div>
          </>
        )}

        {step === 'review' && preview && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                Review extracted case
                {preview.aiUsed && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    <Sparkles className="h-3 w-3" /> AI
                  </span>
                )}
              </DialogTitle>
              <DialogDescription>
                Edit any fields before creating the case.
              </DialogDescription>
            </DialogHeader>

            {preview.notes.length > 0 && (
              <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground space-y-1">
                <p className="font-medium text-foreground flex items-center gap-1">
                  <FileUp className="h-3 w-3" /> Extracted highlights
                </p>
                <ul className="list-disc pl-4 space-y-0.5">
                  {preview.notes.map((n, i) => <li key={i}>{n}</li>)}
                </ul>
              </div>
            )}

            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="title"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Title</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Description</FormLabel>
                      <FormControl>
                        <textarea
                          className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
                          {...field}
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="priority"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Priority</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="low">Low</SelectItem>
                            <SelectItem value="medium">Medium</SelectItem>
                            <SelectItem value="high">High</SelectItem>
                            <SelectItem value="critical">Critical</SelectItem>
                          </SelectContent>
                        </Select>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="category"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Category</FormLabel>
                        <FormControl><Input placeholder="e.g. Fraud, Cybercrime…" {...field} /></FormControl>
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={form.control}
                  name="isPrivate"
                  render={({ field }) => (
                    <FormItem className="flex items-center gap-2 space-y-0">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <FormLabel className="font-normal cursor-pointer">
                        Private case (visible only to assigned team members)
                      </FormLabel>
                    </FormItem>
                  )}
                />

                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => { resetDialog(); }} disabled={isCreating}>
                    Start over
                  </Button>
                  <Button type="submit" disabled={isCreating}>
                    {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Create case
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Case Row ──────────────────────────────────────────────────────────────────

function CaseRow({ c }: { c: CaseReadSlim }) {
  const { mutate: star } = useStarCase();
  const { mutate: unstar } = useUnstarCase();

  function toggleStar(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (c.isStarred) unstar(c.id);
    else star(c.id);
  }

  return (
    <Link
      to={`/cases/${c.id}`}
      className="group flex items-start gap-4 rounded-lg border bg-card p-4 transition-colors hover:bg-accent/40"
    >
      <button
        onClick={toggleStar}
        className="mt-0.5 shrink-0 text-muted-foreground hover:text-amber-400 transition-colors"
        aria-label={c.isStarred ? 'Unstar' : 'Star'}
      >
        <Star
          className={`h-4 w-4 ${c.isStarred ? 'fill-amber-400 text-amber-400' : ''}`}
        />
      </button>

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">{c.referenceNumber}</span>
          <Badge variant={STATUS_VARIANT[c.status]} className="text-xs">
            {STATUS_LABEL[c.status]}
          </Badge>
          <span className={`text-xs font-medium ${PRIORITY_COLOR[c.priority]}`}>
            {PRIORITY_LABEL[c.priority]}
          </span>
          {c.isPrivate && (
            <Badge variant="outline" className="text-xs">
              Private
            </Badge>
          )}
        </div>

        <p className="text-sm font-semibold leading-snug line-clamp-1">{c.title}</p>

        {c.description && (
          <p className="text-xs text-muted-foreground line-clamp-1">{c.description}</p>
        )}

        <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <ListTodo className="h-3 w-3" />
            {c.openTaskCount}/{c.taskCount} tasks
          </span>
          <span className="flex items-center gap-1">
            <StickyNote className="h-3 w-3" />
            {c.noteCount} notes
          </span>
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            {c.assignmentCount} assigned
          </span>
          {c.category && (
            <span className="flex items-center gap-1">
              <FolderKanban className="h-3 w-3" />
              {c.category}
            </span>
          )}
          <span className="flex items-center gap-1 ml-auto">
            <Clock className="h-3 w-3" />
            {formatRelative(c.updatedAt)}
          </span>
        </div>
      </div>

      <ChevronRight className="h-4 w-4 shrink-0 self-center text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
    </Link>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type StatusFilter = 'all' | CaseStatus;
type PriorityFilter = 'all' | CasePriority;

export function CasesPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>('all');
  const [includeArchived, setIncludeArchived] = useState(false);
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const canCreateCase = useHasPermission('case:create');

  const { data, isLoading, isError } = useCases({
    q: search || undefined,
    status: statusFilter === 'all' ? undefined : statusFilter,
    priority: priorityFilter === 'all' ? undefined : priorityFilter,
    includeArchived,
    page,
    pageSize: 20,
  });

  const statusFilters: { label: string; value: StatusFilter }[] = [
    { label: 'All', value: 'all' },
    { label: 'Open', value: 'open' },
    { label: 'In Progress', value: 'in_progress' },
    { label: 'Under Review', value: 'under_review' },
    { label: 'Closed', value: 'closed' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cases"
        description="Every investigation is a workspace — evidence, timeline, tasks, notes, and findings in one place."
        actions={
          canCreateCase ? (
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => setImportOpen(true)}>
                <FileUp className="h-4 w-4" />
                Import from file
              </Button>
              <Button size="sm" onClick={() => setCreateOpen(true)}>
                <Plus className="h-4 w-4" />
                New case
              </Button>
            </div>
          ) : undefined
        }
      />

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search cases…"
            className="pl-9"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <div className="flex items-center gap-2">
          {statusFilters.map((f) => (
            <Button
              key={f.value}
              size="sm"
              variant={statusFilter === f.value ? 'default' : 'outline'}
              onClick={() => {
                setStatusFilter(f.value);
                setPage(1);
              }}
            >
              {f.label}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <Select
            value={priorityFilter}
            onValueChange={(v) => {
              setPriorityFilter(v as PriorityFilter);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-9 w-32">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All priorities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>

          <Button
            size="sm"
            variant={includeArchived ? 'default' : 'outline'}
            onClick={() => setIncludeArchived((v) => !v)}
          >
            <Archive className="h-4 w-4" />
            Archived
          </Button>
        </div>
      </div>

      {/* Stats */}
      {data && (
        <p className="text-sm text-muted-foreground">
          <span className="font-semibold text-foreground">{data.total}</span>{' '}
          {data.total === 1 ? 'case' : 'cases'} found
        </p>
      )}

      {/* Content */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Failed to load cases. Please try again.
        </div>
      )}

      {!isLoading && !isError && data && (
        <>
          {data.items.length === 0 ? (
            <EmptyState
              icon={FolderKanban}
              title="No cases found"
              description={
                search
                  ? `No results for "${search}".`
                  : 'Create your first investigation case to get started.'
              }
              action={
                !search && canCreateCase ? (
                  <Button size="sm" onClick={() => setCreateOpen(true)}>
                    <Plus className="h-4 w-4" />
                    New case
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="space-y-2">
              {data.items.map((c) => (
                <CaseRow key={c.id} c={c} />
              ))}
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

      <CreateCaseDialog open={createOpen} onOpenChange={setCreateOpen} />
      <ImportCaseDialog open={importOpen} onOpenChange={setImportOpen} />
    </div>
  );
}
