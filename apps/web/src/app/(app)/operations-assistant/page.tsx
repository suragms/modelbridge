"use client";

import { useState } from "react";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useOrgId, useToken } from "@/lib/hooks";

export default function OperationsAssistantPage() {
  const token = useToken();
  const orgId = useOrgId();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const ask = async () => {
    if (!token || !question.trim()) return;
    setLoading(true);
    try {
      const data = await api.post<Record<string, unknown>>(
        "/operations-assistant/query",
        { question },
        token,
        orgId ?? undefined
      );
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Operations Assistant</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Ask questions about authorized operational data. Answers include evidence sources and confidence.
        </p>
      </div>
      <Link href="/intelligence" className="text-sm underline">← Intelligence</Link>
      <Card>
        <CardHeader><CardTitle className="text-base">Ask a question</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <textarea
            className="w-full min-h-24 rounded border bg-transparent p-3 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Which provider is performing best this week?"
          />
          <Button onClick={ask} disabled={loading}>{loading ? "Thinking…" : "Ask"}</Button>
        </CardContent>
      </Card>
      {result && (
        <Card>
          <CardHeader><CardTitle className="text-base">Answer</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-2">
            <p>{String(result.answer ?? result.message ?? "")}</p>
            <p className="text-xs text-[var(--muted-foreground)]">
              Confidence: {String(result.confidence ?? "—")} · Sources: {(result.evidence_sources as string[] | undefined)?.join(", ") ?? "—"}
            </p>
            <p className="text-xs italic">{String(result.interpretation ?? "")}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
