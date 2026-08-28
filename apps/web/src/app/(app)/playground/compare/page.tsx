"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowLeft, GitCompare, Send } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useModels, usePlaygroundCompare } from "@/lib/hooks";
import type { PlaygroundCompareResponse, PlaygroundCompareSide } from "@/lib/types";

function SidePanel({ title, side }: { title: string; side: PlaygroundCompareSide }) {
  const text =
    side.success && side.response
      ? side.response.choices[0]?.message?.content ??
        (side.response.choices[0]?.message?.tool_calls
          ? JSON.stringify(side.response.choices[0].message.tool_calls, null, 2)
          : "")
      : side.error ?? "No response";

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>
          {side.success ? (
            <>
              {side.provider ?? "—"} · {side.model}
            </>
          ) : (
            <span className="text-red-600">Failed</span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {side.latency_ms != null && (
            <Badge variant="secondary">{Math.round(side.latency_ms)} ms</Badge>
          )}
          {side.total_tokens != null && (
            <Badge variant="secondary">{side.total_tokens} tokens</Badge>
          )}
          {side.estimated_total_cost != null && (
            <Badge variant="secondary">~${side.estimated_total_cost.toFixed(6)}</Badge>
          )}
        </div>
        <pre className="min-h-[240px] max-h-[480px] overflow-auto rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 p-4 text-sm whitespace-pre-wrap">
          {text}
        </pre>
        {side.request_id && (
          <p className="text-xs text-[var(--muted-foreground)]">Request ID: {side.request_id}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function PlaygroundComparePage() {
  const modelsQuery = useModels();
  const compareMutation = usePlaygroundCompare();

  const [modelA, setModelA] = useState("auto");
  const [modelB, setModelB] = useState("auto");
  const [prompt, setPrompt] = useState("Summarize the benefits of an AI gateway in two bullet points.");
  const [result, setResult] = useState<PlaygroundCompareResponse | null>(null);
  const [error, setError] = useState("");

  const modelOptions = useMemo(() => {
    const models = (modelsQuery.data ?? []).filter((m) => m.is_enabled);
    const chatModels = models.filter(
      (m) => m.supports_chat !== false && !m.supports_embeddings
    );
    return chatModels.length > 0 ? chatModels : models;
  }, [modelsQuery.data]);

  const handleCompare = async () => {
    setError("");
    setResult(null);
    if (modelA === modelB && modelA !== "auto") {
      setError("Choose two different models for a meaningful comparison.");
      return;
    }
    try {
      const res = await compareMutation.mutateAsync({
        model_a: modelA,
        model_b: modelB,
        messages: [{ role: "user", content: prompt }],
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Comparison failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/playground">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" /> Back to playground
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Model Comparison</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Send the same prompt to two models with independent tracked requests
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <GitCompare className="h-4 w-4" /> Compare setup
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="cmp-a">Model A</Label>
              <Select id="cmp-a" value={modelA} onChange={(e) => setModelA(e.target.value)}>
                <option value="auto">auto</option>
                {modelOptions.map((m) => (
                  <option key={m.id} value={m.provider_model_id}>
                    {m.display_name || m.provider_model_id}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cmp-b">Model B</Label>
              <Select id="cmp-b" value={modelB} onChange={(e) => setModelB(e.target.value)}>
                <option value="auto">auto</option>
                {modelOptions.map((m) => (
                  <option key={m.id} value={m.provider_model_id}>
                    {m.display_name || m.provider_model_id}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="cmp-prompt">Prompt</Label>
            <textarea
              id="cmp-prompt"
              className="min-h-[120px] w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>

          <Button onClick={handleCompare} disabled={compareMutation.isPending}>
            <Send className="h-4 w-4" />
            {compareMutation.isPending ? "Comparing…" : "Run comparison"}
          </Button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <div className="grid gap-6 lg:grid-cols-2">
          <SidePanel title="Model A" side={result.side_a} />
          <SidePanel title="Model B" side={result.side_b} />
        </div>
      )}
    </div>
  );
}
