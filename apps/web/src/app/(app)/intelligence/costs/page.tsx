"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIntelligenceCosts } from "@/lib/hooks";

export default function CostIntelligencePage() {
  const q = useIntelligenceCosts();
  const data = q.data as Record<string, unknown> | undefined;
  const models = (data?.by_model as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Cost Intelligence</h1>
      <Link href="/intelligence" className="text-sm underline">← Intelligence</Link>
      <p className="text-xs text-[var(--muted-foreground)]">{String(data?.cost_disclaimer ?? "")}</p>
      <Card>
        <CardHeader><CardTitle className="text-base">Spend Summary</CardTitle></CardHeader>
        <CardContent className="text-sm space-y-1">
          <p>Total: ${Number(data?.total_cost ?? 0).toFixed(4)}</p>
          <p>Actual: ${Number(data?.actual_cost ?? 0).toFixed(4)}</p>
          <p>Estimated: ${Number(data?.estimated_cost ?? 0).toFixed(4)}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">By Model</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {models.map((m) => (
            <div key={String(m.model)} className="flex justify-between text-sm border rounded px-3 py-2">
              <span>{String(m.model)} ({String(m.cost_type)})</span>
              <span>${Number(m.cost).toFixed(4)}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
