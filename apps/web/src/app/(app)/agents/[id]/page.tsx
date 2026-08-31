"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAgent, useAgentExecutions } from "@/lib/hooks";

export default function AgentDetailPage() {
  const params = useParams();
  const id = String(params.id);
  const agent = useAgent(id);
  const executions = useAgentExecutions(id);
  const data = agent.data as Record<string, unknown> | undefined;

  if (agent.isLoading) return <p className="text-sm">Loading…</p>;
  if (!data) return <p className="text-sm">Agent not found.</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/agents" className="text-sm underline">
          ← Agents
        </Link>
        <h1 className="mt-2 text-2xl font-bold">{String(data.name)}</h1>
        <Badge className="mt-2" variant="outline">
          {String(data.status)}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>{String(data.description || "No description")}</p>
          <p>Max steps: {String(data.max_steps)}</p>
          <p>Timeout: {String(data.timeout_seconds)}s</p>
          <pre className="overflow-auto rounded bg-[var(--muted)] p-3 text-xs">
            {JSON.stringify(data.model_configuration, null, 2)}
          </pre>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent executions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(executions.data ?? []).map((e) => (
            <Link
              key={String(e.id)}
              href={`/agents/executions/${e.id}`}
              className="flex justify-between rounded border px-3 py-2 text-sm hover:bg-[var(--muted)]"
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
