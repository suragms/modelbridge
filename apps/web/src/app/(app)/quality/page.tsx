"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQualityOverview } from "@/lib/hooks";

export default function QualityHomePage() {
  const overview = useQualityOverview();
  const data = overview.data as Record<string, unknown> | undefined;
  const regressions = (data?.recent_regressions as Array<Record<string, unknown>>) ?? [];
  const alerts = (data?.recent_alerts as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">AI Quality Engineering</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Evidence-based quality, regression detection, and reliability scorecards.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Overall Quality</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">
              {data?.overall_quality != null ? Number(data.overall_quality).toFixed(2) : "—"}
            </p>
            <p className="text-xs text-[var(--muted-foreground)]">confidence: {String(data?.confidence ?? "n/a")}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Reliability</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">
              {data?.reliability_score != null ? Number(data.reliability_score).toFixed(2) : "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Open Alerts</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{String(data?.open_alerts ?? 0)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Regressions</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{String(data?.regressions_detected ?? 0)}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/quality/pipelines" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Evaluation Pipelines</Link>
        <Link href="/quality/regressions" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Regression Testing</Link>
        <Link href="/quality/models" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Model Comparison</Link>
        <Link href="/quality/production" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Production Monitoring</Link>
        <Link href="/quality/reliability" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Reliability Scorecard</Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Recent Regressions</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {regressions.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No regressions detected.</p>}
            {regressions.map((r) => (
              <div key={String(r.id)} className="flex justify-between rounded border px-3 py-2 text-sm">
                <span>{String(r.baseline)} → {String(r.candidate)}</span>
                <Badge variant="outline">{String(r.status)}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Quality Alerts</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {alerts.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No open alerts.</p>}
            {alerts.map((a) => (
              <div key={String(a.id)} className="rounded border px-3 py-2 text-sm">
                <div className="font-medium">{String(a.title)}</div>
                <Badge variant="outline" className="mt-1">{String(a.type)}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
