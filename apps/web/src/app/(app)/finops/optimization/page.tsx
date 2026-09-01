"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFinopsRecommendations, useFinopsModelComparison } from "@/lib/hooks";

export default function FinopsOptimizationPage() {
  const recs = useFinopsRecommendations();
  const models = useFinopsModelComparison();
  const list = (recs.data as Array<Record<string, unknown>>) ?? [];
  const modelList = (models.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Cost Optimization</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Evidence-based recommendations — projected savings are not realized until measured.
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Recommendations</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No recommendations yet.</p>}
          {list.map((r) => (
            <div key={String(r.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex justify-between">
                <span className="font-medium">{String(r.title)}</span>
                <Badge variant="outline">{String(r.savings_status)}</Badge>
              </div>
              <p className="mt-1">{String(r.description)}</p>
              {r.projected_savings != null && (
                <p className="text-xs text-[var(--muted-foreground)]">
                  Projected: ${Number(r.projected_savings).toFixed(4)} · Risk: {String(r.risk)}
                </p>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Model Cost Comparison</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {modelList.map((m) => (
            <div key={String(m.model)} className="flex justify-between rounded border px-3 py-2 text-sm">
              <span>{String(m.model)} ({String(m.provider)})</span>
              <span>${Number(m.avg_request_cost ?? 0).toFixed(6)}/req</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
