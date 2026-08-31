"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useWorkflowExecution } from "@/lib/hooks";

export default function WorkflowExecutionPage() {
  const params = useParams();
  const id = String(params.id);
  const execution = useWorkflowExecution(id);
  const data = execution.data as Record<string, unknown> | undefined;

  if (execution.isLoading) return <p className="text-sm">Loading…</p>;
  if (!data) return <p className="text-sm">Workflow execution not found.</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/workflows" className="text-sm underline">
          ← Workflows
        </Link>
        <h1 className="mt-2 font-mono text-lg">Workflow run {id.slice(0, 8)}…</h1>
        <Badge className="mt-2" variant="outline">
          {String(data.status)}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Current node: {String(data.current_node_key ?? "—")}</p>
          {data.error_message != null && (
            <p className="text-red-600">{String(data.error_message)}</p>
          )}
          <pre className="overflow-auto rounded bg-[var(--muted)] p-3 text-xs">
            {JSON.stringify(data.context, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
