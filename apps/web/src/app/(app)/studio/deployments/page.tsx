"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStudioDeployments } from "@/lib/hooks";

export default function StudioDeploymentsPage() {
  const deployments = useStudioDeployments();
  const list = (deployments.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Deployment Pipelines</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Draft → Validate → Test → Approval → Deploy → Monitor
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Deployments</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No deployments yet.</p>
          )}
          {list.map((d) => (
            <div key={String(d.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{String(d.name)}</span>
                <Badge variant="outline">{String(d.status)}</Badge>
              </div>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                {String(d.resource_type)} · env: {String(d.environment_id ?? "default")}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
