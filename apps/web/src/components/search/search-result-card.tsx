import { useNavigate } from 'react-router-dom'
import {
  Briefcase,
  FileText,
  MapPin,
  MessageSquare,
  Network,
  NotepadText,
  User,
  Wand2,
} from 'lucide-react'
import type { SearchResultItem, SearchResultType } from '@/types/search'
import { RESULT_TYPE_COLORS, RESULT_TYPE_LABELS } from '@/types/search'

const TYPE_ICON: Record<SearchResultType, React.ElementType> = {
  case: Briefcase,
  evidence: FileText,
  evidence_summary: Wand2,
  entity: Network,
  timeline_event: MapPin,
  note: NotepadText,
  task: MessageSquare,
  user: User,
}

interface Props {
  item: SearchResultItem
  query: string
}

function highlight(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text
  const term = query.trim().split(/\s+/)[0] ?? ''
  if (!term) return text
  const idx = text.toLowerCase().indexOf(term.toLowerCase())
  if (idx < 0) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-yellow-200 text-inherit rounded-sm px-0.5">
        {text.slice(idx, idx + term.length)}
      </mark>
      {text.slice(idx + term.length)}
    </>
  )
}

export function SearchResultCard({ item, query }: Props) {
  const navigate = useNavigate()
  const Icon = TYPE_ICON[item.type] ?? FileText
  const colorClass = RESULT_TYPE_COLORS[item.type]
  const label = RESULT_TYPE_LABELS[item.type]

  return (
    <button
      className="w-full text-left rounded-lg border bg-card px-4 py-3 hover:bg-accent/30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onClick={() => navigate(item.url)}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0 rounded-md bg-muted p-1.5">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${colorClass}`}>
              {label}
            </span>
            {item.caseReference && (
              <span className="text-[11px] text-muted-foreground">{item.caseReference}</span>
            )}
            {item.confidence !== null && item.confidence !== undefined && (
              <span className="text-[11px] text-muted-foreground">
                {Math.round(item.confidence * 100)}% confidence
              </span>
            )}
          </div>

          <p className="text-sm font-medium leading-snug truncate">
            {highlight(item.title, query)}
          </p>

          {item.snippet && (
            <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
              {highlight(item.snippet, query)}
            </p>
          )}

          {item.caseTitle && item.type !== 'case' && (
            <p className="mt-1 text-[11px] text-muted-foreground/70 truncate">
              Case: {item.caseTitle}
            </p>
          )}
        </div>

        <span className="shrink-0 text-[11px] text-muted-foreground/60 mt-0.5">
          {new Date(item.createdAt).toLocaleDateString()}
        </span>
      </div>
    </button>
  )
}
