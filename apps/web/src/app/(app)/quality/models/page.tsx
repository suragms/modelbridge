"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQualityModelComparison } from "@/lib/hooks";

export default function QualityModelsPage() {
  const comparison = useQualityModelComparison();
  const list = (comparison.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Model Quality Comparison</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Aggregated from actual evaluation runs — quality, latency, and failures.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Models</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No evaluation run data yet.</p>}
          {list.map((m) => (
            <div key={String(m.model)} className="rounded border px-3 py-2 text-sm">
              <div className="font-medium">{String(m.model)}</div>
              <p className="text-xs text-[var(--muted-foreground)]">
                pass rate: {m.avg_pass_rate != null ? Number(m.avg_pass_rate).toFixed(2) : "n/a"} ·
                latency: {m.avg_latency_ms != null ? `${Number(m.avg_latency_ms).toFixed(0)}ms` : "n/a"} ·
                failures: {String(m.total_failures ?? 0)}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
