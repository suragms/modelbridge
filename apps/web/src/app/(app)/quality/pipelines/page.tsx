"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQualityPipelines } from "@/lib/hooks";

export default function QualityPipelinesPage() {
  const pipelines = useQualityPipelines();
  const list = (pipelines.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Evaluation Pipelines</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Versioned pipelines with rule, regex, structured, custom, and LLM judge evaluators.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Pipelines</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No pipelines configured.</p>}
          {list.map((p) => (
            <div key={String(p.id)} className="flex justify-between rounded border px-3 py-2 text-sm">
              <span className="font-medium">{String(p.name)}</span>
              <Badge variant="outline">{String(p.status)}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
