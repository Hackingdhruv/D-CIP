import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  MiniMap,
  type Node,
  type NodeTypes,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Network, Search, ZoomIn } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useRelationshipGraph } from '@/hooks/use-ai'
import type { GraphNode, GraphResponse } from '@/types/ai'

// ── Entity type colour map ────────────────────────────────────────────────────

const TYPE_COLOR: Record<string, string> = {
  person: '#3b82f6',
  email: '#22c55e',
  phone: '#14b8a6',
  organization: '#a855f7',
  domain: '#f97316',
  url: '#f97316',
  ip_address: '#ef4444',
  date: '#94a3b8',
  location: '#10b981',
  country: '#10b981',
  city: '#10b981',
  device: '#6366f1',
  os: '#6366f1',
  browser: '#6366f1',
  filename: '#eab308',
  file_hash: '#eab308',
  bank_account: '#ec4899',
  crypto_wallet: '#ec4899',
  vehicle_number: '#06b6d4',
  unknown: '#94a3b8',
}

function nodeColor(type: string) {
  return TYPE_COLOR[type] ?? TYPE_COLOR.unknown
}

// ── Layout: sector-based circle, grouped by entity type ──────────────────────

function computeLayout(
  nodes: GraphNode[]
): Array<{ id: string; x: number; y: number }> {
  const W = 900
  const H = 700
  const cx = W / 2
  const cy = H / 2
  const R = Math.min(W, H) * 0.40

  // Sort by type so same types are adjacent on the circle
  const sorted = [...nodes].sort((a, b) => a.nodeType.localeCompare(b.nodeType))

  return sorted.map((n, i) => {
    const angle = (2 * Math.PI * i) / sorted.length - Math.PI / 2
    return {
      id: n.id,
      x: cx + R * Math.cos(angle) - 70,
      y: cy + R * Math.sin(angle) - 18,
    }
  })
}

// ── Custom node ───────────────────────────────────────────────────────────────

function EntityNode({ data }: { data: { label: string; nodeType: string; confidence: number } }) {
  const color = nodeColor(data.nodeType)
  return (
    <div
      style={{ borderColor: color }}
      className="max-w-[140px] rounded-lg border-2 bg-white px-2 py-1 shadow-sm text-xs cursor-default"
    >
      <div
        style={{ backgroundColor: color }}
        className="mb-0.5 rounded px-1 py-0.5 text-white font-medium text-[10px] inline-block"
      >
        {data.nodeType.replace('_', ' ')}
      </div>
      <p className="truncate font-mono font-semibold leading-tight" title={data.label}>
        {data.label}
      </p>
    </div>
  )
}

const nodeTypes: NodeTypes = { entity: EntityNode }

// ── Convert graph data → React Flow nodes/edges ───────────────────────────────

function toFlow(
  graphData: GraphResponse,
  filter: string
): { nodes: Node[]; edges: Edge[] } {
  const lower = filter.toLowerCase()

  const visibleNodes = graphData.nodes.filter(
    (n) =>
      !filter ||
      n.label.toLowerCase().includes(lower) ||
      n.nodeType.includes(lower)
  )
  const visibleIds = new Set(visibleNodes.map((n) => n.id))

  const positions = computeLayout(visibleNodes)
  const posMap = new Map(positions.map((p) => [p.id, p]))

  const nodes: Node[] = visibleNodes.map((n) => {
    const pos = posMap.get(n.id) ?? { x: 0, y: 0 }
    return {
      id: n.id,
      type: 'entity',
      position: { x: pos.x, y: pos.y },
      data: {
        label: n.label,
        nodeType: n.nodeType,
        confidence: n.confidence,
      },
    }
  })

  const color = '#94a3b8'
  const edges: Edge[] = graphData.edges
    .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
    .map((e) => ({
      id: `${e.source}--${e.target}`,
      source: e.source,
      target: e.target,
      style: {
        stroke: color,
        strokeWidth: Math.min(1 + e.weight * 0.5, 5),
        opacity: 0.6,
      },
      label: e.weight > 1 ? String(e.weight) : undefined,
      labelStyle: { fontSize: 10, fill: '#64748b' },
    }))

  return { nodes, edges }
}

// ── Legend ────────────────────────────────────────────────────────────────────

const LEGEND_TYPES = [
  'person', 'email', 'phone', 'organization', 'domain',
  'ip_address', 'location', 'device', 'file_hash', 'crypto_wallet',
]

function Legend() {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1">
      {LEGEND_TYPES.map((t) => (
        <div key={t} className="flex items-center gap-1">
          <div
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: nodeColor(t) }}
          />
          <span className="text-xs text-muted-foreground">{t.replace('_', ' ')}</span>
        </div>
      ))}
    </div>
  )
}

// ── Inner flow component (needs ReactFlowProvider) ────────────────────────────

function GraphCanvas({ graphData }: { graphData: GraphResponse }) {
  const [filter, setFilter] = useState('')
  const { fitView } = useReactFlow()

  const { nodes: initNodes, edges: initEdges } = useMemo(
    () => toFlow(graphData, filter),
    [graphData, filter]
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(initNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initEdges)

  useEffect(() => {
    const { nodes: n, edges: e } = toFlow(graphData, filter)
    setNodes(n)
    setEdges(e)
    setTimeout(() => fitView({ padding: 0.1 }), 50)
  }, [graphData, filter, setNodes, setEdges, fitView])

  const handleFit = useCallback(() => {
    fitView({ padding: 0.1, duration: 400 })
  }, [fitView])

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="pl-8 h-8 text-sm"
            placeholder="Filter nodes…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <Button variant="outline" size="sm" onClick={handleFit}>
          <ZoomIn className="mr-1.5 h-3.5 w-3.5" />
          Fit
        </Button>
        <span className="text-xs text-muted-foreground">
          {nodes.length} nodes · {edges.length} edges
        </span>
      </div>

      <Legend />

      <div
        className="flex-1 rounded-lg border bg-slate-50 overflow-hidden"
        style={{ minHeight: 480 }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.1 }}
          minZoom={0.2}
          maxZoom={3}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e2e8f0" />
          <Controls showInteractive={false} />
          <MiniMap
            nodeColor={(n) => {
              const nd = n.data as { nodeType?: string }
              return nodeColor(nd?.nodeType ?? 'unknown') ?? '#94a3b8'
            }}
            className="rounded border"
            zoomable
            pannable
          />
        </ReactFlow>
      </div>
    </div>
  )
}

// ── Public export ─────────────────────────────────────────────────────────────

export function GraphTab({ caseId }: { caseId: string }) {
  const { data, isLoading } = useRelationshipGraph(caseId)

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[480px]" />
      </div>
    )
  }

  if (!data || data.nodeCount === 0) {
    return (
      <div className="rounded-lg border border-dashed p-12 text-center">
        <Network className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">
          No entity relationships found. Process evidence through the AI pipeline first.
        </p>
      </div>
    )
  }

  return (
    <ReactFlowProvider>
      <GraphCanvas graphData={data} />
    </ReactFlowProvider>
  )
}
