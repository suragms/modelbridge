"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQualityProduction } from "@/lib/hooks";

export default function QualityProductionPage() {
  const production = useQualityProduction();
  const data = production.data as Record<string, unknown> | undefined;
  const config = (data?.config as Record<string, unknown>) ?? {};
  const samples = (data?.recent_samples as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Production Quality Monitoring</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Governed sampling with redaction — metadata only, no prompt content stored.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Sampling Status</CardTitle></CardHeader>
        <CardContent className="text-sm space-y-1">
          <p>Enabled: {String(config.enabled ?? false)}</p>
          <p>Rate: {String(config.sampling_rate ?? 0)}</p>
          <p>Retention: {String(config.retention_days ?? 30)} days</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Recent Samples</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {samples.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No samples yet.</p>}
          {samples.map((s) => (
            <div key={String(s.request_id)} className="rounded border px-3 py-2 text-xs">
              {String(s.model)} · {String(s.status)} · {String(s.evaluated_at ?? "").slice(0, 19)}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
