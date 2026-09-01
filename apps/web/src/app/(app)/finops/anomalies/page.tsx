"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFinopsAnomalies } from "@/lib/hooks";

export default function FinopsAnomaliesPage() {
  const anomalies = useFinopsAnomalies();
  const list = (anomalies.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Cost Anomalies</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Unusual spending patterns with supporting evidence.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Detected Anomalies</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No anomalies detected.</p>}
          {list.map((a) => (
            <div key={String(a.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex justify-between">
                <span className="font-medium">{String(a.type)}</span>
                <Badge variant="outline">{String(a.status)}</Badge>
              </div>
              <p className="text-xs text-[var(--muted-foreground)]">
                Observed: ${Number(a.observed_value ?? 0).toFixed(4)} · {String(a.detected_at ?? "").slice(0, 19)}
              </p>
              <pre className="mt-1 overflow-x-auto text-xs">{JSON.stringify(a.evidence, null, 2)}</pre>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
