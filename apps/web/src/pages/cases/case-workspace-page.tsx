import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  Archive,
  ArrowLeft,
  CheckSquare,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  MoreHorizontal,
  Pin,
  Plus,
  Search,
  StickyNote,
  Trash2,
  User,
  Users,
} from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useCase,
  useCaseActivities,
  useArchiveCase,
  useRestoreCase,
  useDeleteCase,
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
  useCreateNote,
  useUpdateNote,
  useDeleteNote,
} from '@/hooks/use-cases';
import type {
  CaseRead,
  CaseTaskRead,
  CaseNoteRead,
  TaskStatus,
} from '@/types/case';
import { EvidenceTab } from '@/pages/cases/evidence-tab';
import { AiTab } from '@/pages/cases/ai-tab';
import { GraphTab } from '@/pages/cases/graph-tab';
import { TimelineVisTab } from '@/pages/cases/timeline-vis-tab';
import { ReportsTab } from '@/pages/cases/reports-tab';

// ── Helpers ────────────────────────────────────────────────────────────────────

const STATUS_LABEL: Record<string, string> = {
  draft: 'Draft',
  open: 'Open',
  in_progress: 'In Progress',
  under_review: 'Under Review',
  on_hold: 'On Hold',
  closed: 'Closed',
  archived: 'Archived',
};

const PRIORITY_COLOR: Record<string, string> = {
  low: 'text-slate-500',
  medium: 'text-amber-600',
  high: 'text-orange-600',
  critical: 'text-red-600 font-semibold',
};

const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  pending: 'Pending',
  in_progress: 'In Progress',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

function rel(dateStr: string) {
  const d = new Date(dateStr);
  const diffMs = Date.now() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab({ c }: { c: CaseRead }) {
  const openTasks = c.tasks.filter(
    (t) => t.status === 'pending' || t.status === 'in_progress'
  );
  const pinnedNotes = c.notes.filter((n) => n.isPinned);

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Left column — stats + open tasks + pinned notes */}
      <div className="lg:col-span-2 space-y-6">
        {/* Stat cards */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: 'Tasks', value: c.taskCount, icon: CheckSquare },
            { label: 'Open', value: c.openTaskCount, icon: AlertCircle },
            { label: 'Notes', value: c.noteCount, icon: StickyNote },
            { label: 'Team', value: c.assignmentCount, icon: Users },
          ].map(({ label, value, icon: Icon }) => (
            <Card key={label}>
              <CardContent className="flex items-center gap-3 p-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold leading-none">{value}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Open tasks preview */}
        {openTasks.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Open Tasks</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {openTasks.slice(0, 5).map((t) => (
                <div
                  key={t.id}
                  className="flex items-center gap-3 rounded-md p-2 hover:bg-muted/40 transition-colors"
                >
                  <div
                    className={`h-2 w-2 rounded-full shrink-0 ${
                      t.status === 'in_progress'
                        ? 'bg-blue-500'
                        : 'bg-slate-300'
                    }`}
                  />
                  <span className="flex-1 text-sm line-clamp-1">{t.title}</span>
                  <span
                    className={`text-xs shrink-0 ${PRIORITY_COLOR[t.priority]}`}
                  >
                    {t.priority}
                  </span>
                  {t.dueDate && (
                    <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                      <Clock className="h-3 w-3" />
                      {new Date(t.dueDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                  )}
                </div>
              ))}
              {openTasks.length > 5 && (
                <p className="text-xs text-muted-foreground pl-5">
                  +{openTasks.length - 5} more
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Pinned notes */}
        {pinnedNotes.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Pinned Notes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {pinnedNotes.map((n) => (
                <div key={n.id} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Pin className="h-3 w-3 text-amber-500" />
                    <span className="text-sm font-medium">{n.title}</span>
                  </div>
                  {n.content && (
                    <p className="pl-5 text-xs text-muted-foreground line-clamp-2">
                      {n.content}
                    </p>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Right column — case details */}
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant="outline">{STATUS_LABEL[c.status] ?? c.status}</Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Priority</span>
              <span className={PRIORITY_COLOR[c.priority]}>
                {c.priority.charAt(0).toUpperCase() + c.priority.slice(1)}
              </span>
            </div>
            {c.category && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Category</span>
                <span>{c.category}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Owner</span>
              <span>{c.owner.fullName}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span className="text-xs">{rel(c.createdAt)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Updated</span>
              <span className="text-xs">{rel(c.updatedAt)}</span>
            </div>
            {c.closedAt && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Closed</span>
                <span className="text-xs">{rel(c.closedAt)}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Team */}
        {c.assignments.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Team</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {c.assignments.map((a) => (
                <div key={a.user.id} className="flex items-center gap-2 text-sm">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                    {a.user.fullName.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium">{a.user.fullName}</p>
                    <p className="text-xs text-muted-foreground capitalize">{a.role}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Tags */}
        {c.tags.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Tags</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-1.5">
              {c.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// ── Tasks Tab ─────────────────────────────────────────────────────────────────

const taskSchema = z.object({
  title: z.string().min(1, 'Title is required').max(500),
  description: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high']),
  dueDate: z.string().optional(),
});

type TaskFormValues = z.infer<typeof taskSchema>;

function TaskDialog({
  caseId,
  open,
  onOpenChange,
}: {
  caseId: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { mutateAsync, isPending } = useCreateTask(caseId);
  const form = useForm<TaskFormValues>({
    resolver: zodResolver(taskSchema),
    defaultValues: { title: '', description: '', priority: 'medium', dueDate: '' },
  });

  async function onSubmit(values: TaskFormValues) {
    await mutateAsync({
      title: values.title,
      description: values.description || undefined,
      priority: values.priority,
      dueDate: values.dueDate || undefined,
    });
    form.reset();
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New Task</DialogTitle>
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
                    <Input autoFocus placeholder="Task title…" {...field} />
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
                      className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                      placeholder="Optional details…"
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
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="dueDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Due date</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create task
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

function TaskRow({ task, caseId }: { task: CaseTaskRead; caseId: string }) {
  const { mutate: update } = useUpdateTask(caseId);
  const { mutate: del } = useDeleteTask(caseId);

  function cycleStatus() {
    const next: Record<TaskStatus, TaskStatus> = {
      pending: 'in_progress',
      in_progress: 'completed',
      completed: 'pending',
      cancelled: 'pending',
    };
    update({ taskId: task.id, data: { status: next[task.status] } });
  }


  return (
    <div className="flex items-start gap-3 rounded-md border bg-card p-3 hover:bg-accent/30 transition-colors">
      <button
        onClick={cycleStatus}
        title={`Status: ${TASK_STATUS_LABEL[task.status]}`}
        aria-label={`Cycle task status (current: ${TASK_STATUS_LABEL[task.status]})`}
        className="mt-0.5 shrink-0"
      >
        <div
          className={`h-4 w-4 rounded-full border-2 border-border ${
            task.status === 'completed' ? 'bg-green-500 border-green-500' : 'bg-background'
          }`}
        />
      </button>

      <div className="min-w-0 flex-1">
        <p
          className={`text-sm font-medium ${
            task.status === 'completed' ? 'line-through text-muted-foreground' : ''
          }`}
        >
          {task.title}
        </p>
        {task.description && (
          <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
            {task.description}
          </p>
        )}
        <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
          <span className={`font-medium ${PRIORITY_COLOR[task.priority]}`}>
            {task.priority}
          </span>
          {task.dueDate && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {new Date(task.dueDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          )}
          {task.assignee && (
            <span className="flex items-center gap-1">
              <User className="h-3 w-3" />
              {task.assignee.fullName}
            </span>
          )}
        </div>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onClick={() =>
              update({
                taskId: task.id,
                data: {
                  status:
                    task.status === 'completed'
                      ? 'pending'
                      : 'completed',
                },
              })
            }
          >
            {task.status === 'completed' ? 'Mark pending' : 'Mark complete'}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive"
            onClick={() => del(task.id)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

function TasksTab({ c }: { c: CaseRead }) {
  const [createOpen, setCreateOpen] = useState(false);
  const [filter, setFilter] = useState<'all' | TaskStatus>('all');

  const filtered =
    filter === 'all' ? c.tasks : c.tasks.filter((t) => t.status === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {(['all', 'pending', 'in_progress', 'completed'] as const).map((s) => (
            <Button
              key={s}
              size="sm"
              variant={filter === s ? 'default' : 'outline'}
              onClick={() => setFilter(s)}
            >
              {s === 'all' ? 'All' : TASK_STATUS_LABEL[s as TaskStatus]}
            </Button>
          ))}
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          Add task
        </Button>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          No tasks{filter !== 'all' ? ` with status "${filter}"` : ''}.
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((t) => (
            <TaskRow key={t.id} task={t} caseId={c.id} />
          ))}
        </div>
      )}

      <TaskDialog caseId={c.id} open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}

// ── Notes Tab ─────────────────────────────────────────────────────────────────

const noteSchema = z.object({
  title: z.string().min(1, 'Title is required').max(500),
  content: z.string().default(''),
  isPinned: z.boolean(),
});

type NoteFormValues = z.infer<typeof noteSchema>;

function NoteDialog({
  caseId,
  open,
  onOpenChange,
}: {
  caseId: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { mutateAsync, isPending } = useCreateNote(caseId);
  const form = useForm<NoteFormValues>({
    resolver: zodResolver(noteSchema),
    defaultValues: { title: '', content: '', isPinned: false },
  });

  async function onSubmit(values: NoteFormValues) {
    await mutateAsync(values);
    form.reset();
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New Note</DialogTitle>
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
                    <Input autoFocus placeholder="Note title…" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="content"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Content</FormLabel>
                  <FormControl>
                    <textarea
                      className="flex min-h-[160px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y"
                      placeholder="Write your investigation note here…"
                      {...field}
                    />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="isPinned"
              render={({ field }) => (
                <FormItem className="flex items-center gap-2 space-y-0">
                  <FormControl>
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-primary"
                      checked={field.value}
                      onChange={field.onChange}
                    />
                  </FormControl>
                  <FormLabel className="cursor-pointer">Pin this note</FormLabel>
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save note
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

function NoteCard({ note, caseId }: { note: CaseNoteRead; caseId: string }) {
  const { mutate: update } = useUpdateNote(caseId);
  const { mutate: del } = useDeleteNote(caseId);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            {note.isPinned && <Pin className="h-3.5 w-3.5 shrink-0 text-amber-500" />}
            <h4 className="text-sm font-semibold">{note.title}</h4>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() =>
                  update({ noteId: note.id, data: { isPinned: !note.isPinned } })
                }
              >
                {note.isPinned ? 'Unpin' : 'Pin'}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => del(note.id)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {note.content && (
          <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
            {note.content}
          </p>
        )}

        <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
          <span>{note.createdBy.fullName}</span>
          <span>·</span>
          <span>{rel(note.updatedAt)}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function NotesTab({ c }: { c: CaseRead }) {
  const [createOpen, setCreateOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filtered = c.notes.filter(
    (n) =>
      !search ||
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.content.toLowerCase().includes(search.toLowerCase())
  );
  const pinned = filtered.filter((n) => n.isPinned);
  const rest = filtered.filter((n) => !n.isPinned);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Search notes…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          Add note
        </Button>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          {search ? `No notes matching "${search}".` : 'No notes yet. Add the first one.'}
        </div>
      ) : (
        <div className="space-y-4">
          {pinned.length > 0 && (
            <div className="space-y-3">
              <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <Pin className="h-3 w-3" /> Pinned
              </h4>
              {pinned.map((n) => (
                <NoteCard key={n.id} note={n} caseId={c.id} />
              ))}
            </div>
          )}
          {rest.length > 0 && (
            <div className="space-y-3">
              {pinned.length > 0 && (
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Notes
                </h4>
              )}
              {rest.map((n) => (
                <NoteCard key={n.id} note={n} caseId={c.id} />
              ))}
            </div>
          )}
        </div>
      )}

      <NoteDialog caseId={c.id} open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}

// ── Activity Tab ──────────────────────────────────────────────────────────────

function ActivityTab({ caseId }: { caseId: string }) {
  const { data, isLoading } = useCaseActivities(caseId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12" />
        ))}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
        No activity recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {data.map((a) => (
        <div
          key={a.id}
          className="flex items-start gap-3 rounded-md p-3 hover:bg-muted/40 transition-colors"
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
            <Activity className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm">{a.description}</p>
            <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
              {a.actor && <span>{a.actor.fullName}</span>}
              <span>·</span>
              <span>{rel(a.createdAt)}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main Workspace ────────────────────────────────────────────────────────────

export function CaseWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: c, isLoading, isError } = useCase(id!);
  const { mutate: archive, isPending: archiving } = useArchiveCase();
  const { mutate: restore, isPending: restoring } = useRestoreCase();
  const { mutate: del, isPending: deleting } = useDeleteCase();
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (isError || !c) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        Case not found or you do not have access.{' '}
        <Link to="/cases" className="underline">
          Back to cases
        </Link>
      </div>
    );
  }

  function handleDelete() {
    setConfirmDeleteOpen(true);
  }

  function confirmDelete() {
    del(c!.id, { onSuccess: () => navigate('/cases') });
    setConfirmDeleteOpen(false);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Link to="/cases" className="flex items-center gap-1 hover:text-foreground">
              <ArrowLeft className="h-3.5 w-3.5" />
              Cases
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="font-mono">{c.referenceNumber}</span>
          </div>
          <h1 className="text-xl font-semibold tracking-tight">{c.title}</h1>
          {c.description && (
            <p className="max-w-2xl text-sm text-muted-foreground">{c.description}</p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                Actions
                <ChevronDown className="ml-1 h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {c.archivedAt ? (
                <DropdownMenuItem
                  disabled={restoring}
                  onClick={() => restore(c.id)}
                >
                  <Archive className="mr-2 h-4 w-4" />
                  Restore case
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem
                  disabled={archiving}
                  onClick={() => archive(c.id)}
                >
                  <Archive className="mr-2 h-4 w-4" />
                  Archive case
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                disabled={deleting}
                onClick={handleDelete}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete case
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Delete confirmation */}
      <Dialog open={confirmDeleteOpen} onOpenChange={setConfirmDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete case</DialogTitle>
            <DialogDescription>
              This will permanently delete <strong>{c.referenceNumber}</strong> and all associated data. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" disabled={deleting} onClick={confirmDelete}>
              {deleting ? 'Deleting…' : 'Delete case'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <div className="overflow-x-auto">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="tasks">
            Tasks
            {c.openTaskCount > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-xs">
                {c.openTaskCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="evidence">
            Evidence
          </TabsTrigger>
          <TabsTrigger value="ai">
            AI
          </TabsTrigger>
          <TabsTrigger value="timeline">
            Timeline
          </TabsTrigger>
          <TabsTrigger value="graph">
            Graph
          </TabsTrigger>
          <TabsTrigger value="reports">
            Reports
          </TabsTrigger>
        </TabsList>
        </div>

        <TabsContent value="overview" className="mt-6">
          <OverviewTab c={c} />
        </TabsContent>

        <TabsContent value="tasks" className="mt-6">
          <TasksTab c={c} />
        </TabsContent>

        <TabsContent value="notes" className="mt-6">
          <NotesTab c={c} />
        </TabsContent>

        <TabsContent value="activity" className="mt-6">
          <ActivityTab caseId={c.id} />
        </TabsContent>

        <TabsContent value="evidence" className="mt-6">
          <EvidenceTab caseId={c.id} />
        </TabsContent>

        <TabsContent value="ai" className="mt-6">
          <AiTab caseId={c.id} />
        </TabsContent>

        <TabsContent value="timeline" className="mt-6">
          <TimelineVisTab caseId={c.id} />
        </TabsContent>

        <TabsContent value="graph" className="mt-6">
          <GraphTab caseId={c.id} />
        </TabsContent>

        <TabsContent value="reports" className="mt-6">
          <ReportsTab caseId={c.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
