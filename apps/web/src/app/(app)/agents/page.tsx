"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAgentExecutions, useAgents, useAgentsOverview } from "@/lib/hooks";

export default function AgentsPage() {
  const overview = useAgentsOverview();
  const agents = useAgents();
  const executions = useAgentExecutions();
  const data = overview.data as Record<string, number | null> | undefined;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">AI Agents</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Persistent agent definitions, executions, and observability for this organization.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Total agents", data?.total_agents],
          ["Active agents", data?.active_agents],
          ["Recent executions", data?.recent_executions],
          ["Success rate", data?.success_rate != null ? `${((data.success_rate as number) * 100).toFixed(1)}%` : "—"],
        ].map(([label, value]) => (
          <Card key={String(label)}>
            <CardHeader className="pb-2">
              <CardDescription>{label}</CardDescription>
              <CardTitle className="text-2xl">{overview.isLoading ? "…" : (value ?? 0)}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Agents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(agents.data ?? []).length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No agents defined yet.</p>
          )}
          {(agents.data ?? []).map((a) => (
            <Link
              key={String(a.id)}
              href={`/agents/${a.id}`}
              className="flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-2 text-sm hover:bg-[var(--muted)]"
            >
              <span>{String(a.name)}</span>
              <Badge variant="outline">{String(a.status)}</Badge>
            </Link>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent executions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(executions.data ?? []).slice(0, 10).map((e) => (
            <Link
              key={String(e.id)}
              href={`/agents/executions/${e.id}`}
              className="flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-2 text-sm hover:bg-[var(--muted)]"
            >
              <span className="font-mono text-xs">{String(e.id).slice(0, 8)}…</span>
              <Badge variant="outline">{String(e.status)}</Badge>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
