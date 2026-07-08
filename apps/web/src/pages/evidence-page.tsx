import { FileBox } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { EmptyState } from '@/components/common/empty-state';

export function EvidencePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence"
        description="Ingested items with their integrity hashes and chain of custody. Originals are stored immutably; derived artifacts stay separate."
      />
      <EmptyState
        icon={FileBox}
        title="No evidence ingested"
        description="Evidence is managed inside each case workspace. Open a case and navigate to the Evidence tab to upload and review items."
      />
    </div>
  );
}
