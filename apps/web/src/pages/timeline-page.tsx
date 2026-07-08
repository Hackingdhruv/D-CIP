import { Clock } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { EmptyState } from '@/components/common/empty-state';

export function TimelinePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Timeline"
        description="A unified chronology of events reconstructed from evidence across a case."
      />
      <EmptyState
        icon={Clock}
        title="No events to plot"
        description="As evidence is processed, dated events are extracted and laid out here as an interactive chronology."
      />
    </div>
  );
}
