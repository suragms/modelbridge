"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEvaluationDatasets } from "@/lib/hooks";

export default function StudioDatasetsPage() {
  const datasets = useEvaluationDatasets();
  const list = (datasets.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Evaluation Datasets</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Organization-scoped test cases for reproducible evaluation runs.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Datasets</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No datasets configured.</p>
          )}
          {list.map((d) => (
            <div key={String(d.id)} className="rounded border px-3 py-2 text-sm">
              <div className="font-medium">{String(d.name)}</div>
              <p className="text-xs text-[var(--muted-foreground)]">
                v{String(d.version)} · {String(d.test_case_count)} cases
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
