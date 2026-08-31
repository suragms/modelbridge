"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useModels, useStudioCompare } from "@/lib/hooks";

export default function StudioPlaygroundPage() {
  const models = useModels();
  const compare = useStudioCompare();
  const modelList = (models.data as Array<Record<string, unknown>>) ?? [];
  const [prompt, setPrompt] = useState("Explain quantum computing in one sentence.");
  const [selectedModels, setSelectedModels] = useState<string[]>(["auto"]);
  const [results, setResults] = useState<Array<Record<string, unknown>>>([]);

  const toggleModel = (modelId: string) => {
    setSelectedModels((prev) =>
      prev.includes(modelId) ? prev.filter((m) => m !== modelId) : [...prev, modelId]
    );
  };

  const runCompare = () => {
    compare.mutate(
      {
        messages: [{ role: "user", content: prompt }],
        models: selectedModels.length ? selectedModels : ["auto"],
      },
      {
        onSuccess: (res) => {
          const data = res as Record<string, unknown>;
          setResults((data.comparisons as Array<Record<string, unknown>>) ?? []);
        },
      }
    );
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Prompt Playground</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Test prompts and compare models through the real ModelBridge request pipeline.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Input</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            className="w-full rounded border px-3 py-2 text-sm"
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <div>
            <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">Models to compare</p>
            <div className="flex flex-wrap gap-2">
              {modelList.slice(0, 8).map((m) => {
                const id = String(m.id ?? m.model_id ?? m.name);
                const active = selectedModels.includes(id);
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => toggleModel(id)}
                    className={`rounded border px-2 py-1 text-xs ${active ? "bg-[var(--muted)]" : ""}`}
                  >
                    {id}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => toggleModel("auto")}
                className={`rounded border px-2 py-1 text-xs ${selectedModels.includes("auto") ? "bg-[var(--muted)]" : ""}`}
              >
                auto
              </button>
            </div>
          </div>
          <Button onClick={runCompare} disabled={compare.isPending}>
            Run Comparison
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {results.map((r, i) => (
          <Card key={i}>
            <CardHeader>
              <CardTitle className="text-sm">{String(r.model)}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {r.error ? (
                <p className="text-red-600">{String(r.error)}</p>
              ) : (
                <>
                  <p>{String(r.output ?? "")}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    {String(r.latency_ms)}ms · tokens: {String(r.tokens ?? 0)} · cost (
                    {String(r.cost_type)}): {String(r.estimated_cost ?? "n/a")}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
