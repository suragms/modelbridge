"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { WorkflowCanvas } from "@/components/studio/workflow-canvas";
import {
  useCreateStudioWorkflow,
  usePublishStudioWorkflow,
  useStudioWorkflow,
  useStudioWorkflows,
  useUpdateStudioWorkflow,
} from "@/lib/hooks";

export default function StudioWorkflowsPage() {
  const workflows = useStudioWorkflows();
  const createWorkflow = useCreateStudioWorkflow();
  const publishWorkflow = usePublishStudioWorkflow();
  const updateWorkflow = useUpdateStudioWorkflow();
  const list = (workflows.data as Array<Record<string, unknown>>) ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detail = useStudioWorkflow(selectedId);

  const visual = (detail.data as Record<string, unknown> | undefined)?.visual_definition as
    | { nodes: unknown[]; edges: unknown[] }
    | undefined;

  const handleCreate = () => {
    const name = `Workflow ${list.length + 1}`;
    createWorkflow.mutate(
      {
        name,
        visual_definition: {
          nodes: [
            { id: "trigger-1", type: "trigger", config: {} },
            { id: "output-1", type: "output", config: {} },
          ],
          edges: [{ source: "trigger-1", target: "output-1" }],
        },
      },
      {
        onSuccess: (res) => {
          const id = (res as Record<string, string>).workflow_id;
          if (id) setSelectedId(id);
          workflows.refetch();
        },
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workflow Builder</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Visual workflows compile to the existing workflow execution engine on publish.
          </p>
        </div>
        <Button onClick={handleCreate} disabled={createWorkflow.isPending}>
          New Workflow
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Workflows</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {list.length === 0 && (
              <p className="text-sm text-[var(--muted-foreground)]">No workflows yet.</p>
            )}
            {list.map((wf) => (
              <button
                key={String(wf.id)}
                type="button"
                onClick={() => setSelectedId(String(wf.id))}
                className={`w-full rounded border px-3 py-2 text-left text-sm ${
                  selectedId === String(wf.id) ? "border-[var(--primary)] bg-[var(--muted)]" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{String(wf.name)}</span>
                  <Badge variant="outline">{String(wf.status)}</Badge>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-4">
          {selectedId ? (
            <>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => publishWorkflow.mutate(selectedId, { onSuccess: () => workflows.refetch() })}
                  disabled={publishWorkflow.isPending}
                >
                  Publish
                </Button>
                <Link href={`/workflows`} className="text-sm underline self-center">
                  Open execution view
                </Link>
              </div>
              <WorkflowCanvas
                initial={visual as { nodes: []; edges: [] } | undefined}
                onSave={(v) => {
                  if (!selectedId) return;
                  updateWorkflow.mutate({
                    id: selectedId,
                    body: { visual_definition: v, change_summary: "Canvas save" },
                  });
                }}
              />
            </>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-sm text-[var(--muted-foreground)]">
                Select or create a workflow to open the canvas.
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
