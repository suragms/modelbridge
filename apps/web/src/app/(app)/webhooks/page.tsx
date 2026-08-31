"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useWebhooks } from "@/lib/hooks";

export default function WebhooksPage() {
  const webhooks = useWebhooks();
  const list = (webhooks.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Webhooks</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Outbound event delivery endpoints with signed payloads and retry tracking.
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Endpoints</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No webhooks configured. Use the API or CLI to create one.</p>
          )}
          {list.map((w) => (
            <div key={String(w.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{String(w.name)}</span>
                <Badge variant="outline">{String(w.status)}</Badge>
              </div>
              <p className="mt-1 truncate font-mono text-xs text-[var(--muted-foreground)]">{String(w.url)}</p>
              <p className="mt-1 text-xs">Events: {((w.event_types as string[]) ?? []).join(", ")}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
