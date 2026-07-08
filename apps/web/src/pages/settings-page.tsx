import { Settings } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { EmptyState } from '@/components/common/empty-state';

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Your profile, preferences, and personal workspace configuration."
      />
      <EmptyState
        icon={Settings}
        title="No configurable settings yet"
        description="Platform-wide settings will appear here. For your profile, notifications, and account preferences, visit the Profile page."
      />
    </div>
  );
}
