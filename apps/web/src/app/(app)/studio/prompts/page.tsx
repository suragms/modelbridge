"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCreatePrompt, usePrompts, useTestPrompt } from "@/lib/hooks";

export default function StudioPromptsPage() {
  const prompts = usePrompts();
  const createPrompt = useCreatePrompt();
  const testPrompt = useTestPrompt();
  const list = (prompts.data as Array<Record<string, unknown>>) ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [testInput, setTestInput] = useState("Hello");
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null);

  const handleCreate = () => {
    createPrompt.mutate(
      {
        name: `Prompt ${list.length + 1}`,
        content: "You are a helpful assistant for {{customer_name}}.",
        change_notes: "Initial version",
      },
      { onSuccess: () => prompts.refetch() }
    );
  };

  const handleTest = () => {
    if (!selectedId) return;
    testPrompt.mutate(
      { id: selectedId, input: testInput, variables: { customer_name: "User" } },
      { onSuccess: (res) => setTestResult(res as Record<string, unknown>) }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Prompt Studio</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Versioned prompt templates with validated variables.
          </p>
        </div>
        <Button onClick={handleCreate} disabled={createPrompt.isPending}>
          New Prompt
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Templates</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {list.map((p) => (
              <button
                key={String(p.id)}
                type="button"
                onClick={() => setSelectedId(String(p.id))}
                className={`w-full rounded border px-3 py-2 text-left text-sm ${
                  selectedId === String(p.id) ? "border-[var(--primary)] bg-[var(--muted)]" : ""
                }`}
              >
                <div className="font-medium">{String(p.name)}</div>
                <div className="text-xs text-[var(--muted-foreground)]">
                  usage: {String(p.usage_count ?? 0)}
                </div>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Test</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <textarea
              className="w-full rounded border px-2 py-1 text-sm"
              rows={3}
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              placeholder="Test input"
            />
            <Button size="sm" onClick={handleTest} disabled={!selectedId || testPrompt.isPending}>
              Run via Gateway
            </Button>
            {testResult && (
              <div className="rounded border p-3 text-xs space-y-1">
                <p>{String(testResult.output ?? "")}</p>
                <p className="text-[var(--muted-foreground)]">
                  {String(testResult.latency_ms)}ms · cost ({String(testResult.cost_type)}):{" "}
                  {String(testResult.estimated_cost ?? "n/a")}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
