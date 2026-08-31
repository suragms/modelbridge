"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useWorkflowExecutions, useWorkflows } from "@/lib/hooks";

export default function WorkflowsPage() {
  const workflows = useWorkflows();
  const executions = useWorkflowExecutions();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Workflows</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Multi-step orchestration with agents, tools, conditions, and approvals.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Workflow definitions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(workflows.data ?? []).length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No workflows yet.</p>
          )}
          {(workflows.data ?? []).map((w) => (
            <div
              key={String(w.id)}
              className="flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-2 text-sm"
            >
              <span>{String(w.name)}</span>
              <Badge variant="outline">{String(w.status)}</Badge>
            </div>
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
              href={`/workflows/executions/${e.id}`}
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
