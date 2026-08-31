"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIntegrations } from "@/lib/hooks";

export default function IntegrationsPage() {
  const integrations = useIntegrations();
  const list = (integrations.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Connected external services. GitHub integration supports PAT verification and signed inbound webhooks.
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Connected Integrations</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No integrations connected yet.</p>
          )}
          {list.map((i) => (
            <div key={String(i.id)} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <div>
                <span className="font-medium">{String(i.name)}</span>
                <span className="ml-2 text-xs text-[var(--muted-foreground)]">{String(i.provider)}</span>
              </div>
              <Badge variant="outline">{String(i.status)}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
