"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIntelligenceAnomalies } from "@/lib/hooks";

export default function AnomaliesPage() {
  const q = useIntelligenceAnomalies();
  const list = (q.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Anomalies</h1>
      <Link href="/intelligence" className="text-sm underline">← Intelligence</Link>
      <Card>
        <CardHeader><CardTitle className="text-base">Detected Anomalies</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No anomalies recorded.</p>}
          {list.map((a) => (
            <div key={String(a.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex justify-between">
                <span className="font-medium">{String(a.metric)}</span>
                <Badge variant="outline">{String(a.severity)}</Badge>
              </div>
              <p className="text-[var(--muted-foreground)]">Observed: {String(a.observed_value)}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
