"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQualityRegressions } from "@/lib/hooks";

export default function QualityRegressionsPage() {
  const regressions = useQualityRegressions();
  const list = (regressions.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Regression Testing</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Baseline vs candidate comparisons with measurable evidence — no regression claims without data.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Comparisons</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No regression comparisons yet.</p>}
          {list.map((r) => (
            <div key={String(r.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex justify-between">
                <span>{String(r.baseline)} → {String(r.candidate)}</span>
                <Badge variant="outline">{String(r.status)}</Badge>
              </div>
              <pre className="mt-2 overflow-x-auto text-xs text-[var(--muted-foreground)]">
                {JSON.stringify(r.differences, null, 2)}
              </pre>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
