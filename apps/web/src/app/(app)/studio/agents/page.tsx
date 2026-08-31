"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStudioAgents } from "@/lib/hooks";

export default function StudioAgentsPage() {
  const agents = useStudioAgents();
  const list = (agents.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Agent Builder</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Configure agents connected to Phase 9 agent infrastructure with safety limits enforced server-side.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Organization Agents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No agents configured.</p>
          )}
          {list.map((a) => (
            <div key={String(a.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{String(a.name)}</span>
                <Badge variant="outline">{String(a.status)}</Badge>
              </div>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                max steps: {String(a.max_steps)} · timeout: {String(a.timeout_seconds)}s
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
