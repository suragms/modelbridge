"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFinopsCosts } from "@/lib/hooks";

export default function FinopsExplorerPage() {
  const costs = useFinopsCosts();
  const data = costs.data as Record<string, unknown> | undefined;
  const breakdown = (data?.breakdown as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Cost Explorer</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Filter and break down costs by provider, model, and more.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Summary</CardTitle></CardHeader>
        <CardContent className="text-sm space-y-1">
          <p>Total: ${Number(data?.total_cost ?? 0).toFixed(4)}</p>
          <p>Type: {String(data?.cost_type ?? "unknown")}</p>
          <p>Period: {String(data?.period_days ?? 30)} days</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Breakdown</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {breakdown.map((b) => (
            <div key={String(b.key)} className="flex justify-between rounded border px-3 py-2 text-sm">
              <span>{String(b.key)}</span>
              <span>${Number(b.cost ?? 0).toFixed(4)} ({String(b.requests)} reqs)</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
