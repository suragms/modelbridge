"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAgentExecution } from "@/lib/hooks";

export default function AgentExecutionPage() {
  const params = useParams();
  const id = String(params.id);
  const execution = useAgentExecution(id);
  const data = execution.data as Record<string, unknown> | undefined;
  const steps = (data?.steps as Array<Record<string, unknown>>) ?? [];

  if (execution.isLoading) return <p className="text-sm">Loading…</p>;
  if (!data) return <p className="text-sm">Execution not found.</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/agents" className="text-sm underline">
          ← Agents
        </Link>
        <h1 className="mt-2 font-mono text-lg">Execution {id.slice(0, 8)}…</h1>
        <Badge className="mt-2" variant="outline">
          {String(data.status)}
        </Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Steps</CardTitle>
          </CardHeader>
          <CardContent>{String(data.total_steps)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Tokens</CardTitle>
          </CardHeader>
          <CardContent>{String(data.total_tokens)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Est. cost</CardTitle>
          </CardHeader>
          <CardContent>
            {data.estimated_cost_usd != null ? `$${Number(data.estimated_cost_usd).toFixed(4)}` : "—"}
          </CardContent>
        </Card>
      </div>

      {data.output_text != null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Output</CardTitle>
          </CardHeader>
          <CardContent className="whitespace-pre-wrap text-sm">{String(data.output_text)}</CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Timeline</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {steps.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No steps recorded yet.</p>
          )}
          {steps.map((s) => (
            <div key={String(s.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex justify-between">
                <span>
                  #{String(s.step_number)} {String(s.step_type)}
                  {s.tool_name ? ` · ${String(s.tool_name)}` : ""}
                </span>
                <Badge variant="outline">{String(s.status)}</Badge>
              </div>
              {s.latency_ms != null && (
                <p className="text-xs text-[var(--muted-foreground)]">{Number(s.latency_ms).toFixed(0)} ms</p>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
