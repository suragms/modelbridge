"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIntelligenceOverview } from "@/lib/hooks";

export default function IntelligencePage() {
  const overview = useIntelligenceOverview();
  const data = overview.data as Record<string, unknown> | undefined;
  const recs = (data?.recommendations as Array<Record<string, unknown>>) ?? [];
  const anomalies = (data?.anomalies as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Intelligence</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Evidence-based operational intelligence from real telemetry.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Health</CardTitle></CardHeader>
          <CardContent>
            <Badge variant="outline">{String(data?.operational_health ?? "unknown")}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Recommendations</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{String(data?.active_recommendations ?? 0)}</p>
            <Link href="/intelligence/recommendations" className="text-xs underline">Review</Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Anomalies</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{String(data?.open_anomalies ?? 0)}</p>
            <Link href="/intelligence/anomalies" className="text-xs underline">View</Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Assistant</CardTitle></CardHeader>
          <CardContent>
            <Link href="/operations-assistant" className="text-xs underline">Ask a question</Link>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/intelligence/providers" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Provider Intelligence</Link>
        <Link href="/intelligence/costs" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Cost Intelligence</Link>
        <Link href="/intelligence/capacity" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Capacity</Link>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Recent Recommendations</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {recs.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No open recommendations.</p>}
          {recs.map((r) => (
            <div key={String(r.id)} className="flex justify-between rounded border px-3 py-2 text-sm">
              <span>{String(r.title)}</span>
              <Badge variant="outline">{String(r.category)}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Recent Anomalies</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {anomalies.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No anomalies detected.</p>}
          {anomalies.map((a) => (
            <div key={String(a.id)} className="flex justify-between rounded border px-3 py-2 text-sm">
              <span>{String(a.metric)}</span>
              <Badge variant="outline">{String(a.severity)}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
