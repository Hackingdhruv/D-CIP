import { Share2 } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { EmptyState } from '@/components/common/empty-state';

export function GraphPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Relationships"
        description="Entities and the connections between them, rendered as an explorable graph backed by Neo4j."
      />
      <EmptyState
        icon={Share2}
        title="No relationships mapped"
        description="Once entities are extracted from evidence, their links appear here as an interactive node graph."
      />
    </div>
  );
}
