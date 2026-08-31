"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIntelligenceRecommendations } from "@/lib/hooks";

export default function RecommendationsPage() {
  const q = useIntelligenceRecommendations();
  const list = (q.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Recommendations</h1>
      <Link href="/intelligence" className="text-sm underline">← Intelligence</Link>
      <Card>
        <CardHeader><CardTitle className="text-base">Active Recommendations</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {list.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No recommendations.</p>}
          {list.map((r) => (
            <div key={String(r.id)} className="rounded border px-3 py-3 text-sm space-y-1">
              <div className="flex justify-between gap-2">
                <span className="font-medium">{String(r.title)}</span>
                <Badge variant="outline">{String(r.status)}</Badge>
              </div>
              <p>{String(r.description)}</p>
              <p className="text-xs text-[var(--muted-foreground)]">
                Confidence: {String(r.confidence)} · {String(r.category)}
              </p>
              {r.suggested_action ? (
                <p className="text-xs">Suggested: {String(r.suggested_action)}</p>
              ) : null}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
