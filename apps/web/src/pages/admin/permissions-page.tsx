import { PageHeader } from '@/components/common/page-header';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { usePermissions } from '@/hooks/use-roles';

export function PermissionsPage() {
  const { data: permissions, isLoading } = usePermissions();

  const grouped = (permissions ?? []).reduce<Record<string, typeof permissions>>(
    (acc, p) => {
      if (!acc[p.resource]) acc[p.resource] = [];
      acc[p.resource]!.push(p);
      return acc;
    },
    {},
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Permissions"
        description="All granular permissions available in the platform. Permissions are assigned to roles."
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(grouped).map(([resource, perms]) => (
            <Card key={resource}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  {resource}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2 pt-0">
                {perms!.map((p) => (
                  <Badge key={p.id} variant="outline" className="font-mono text-xs">
                    {p.codename}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
