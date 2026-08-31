"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIntelligenceProviders } from "@/lib/hooks";

export default function ProviderIntelligencePage() {
  const q = useIntelligenceProviders();
  const data = q.data as Record<string, unknown> | undefined;
  const providers = (data?.providers as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Provider Intelligence</h1>
      <Link href="/intelligence" className="text-sm underline">← Intelligence</Link>
      {data?.status === "insufficient_data" && (
        <p className="text-sm text-[var(--muted-foreground)]">{String(data?.message)}</p>
      )}
      <Card>
        <CardHeader><CardTitle className="text-base">Performance Analysis</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {providers.map((p) => (
            <div key={String(p.provider)} className="rounded border px-3 py-2 text-sm">
              <div className="font-medium">{String(p.provider)}</div>
              <div className="text-[var(--muted-foreground)]">{String(p.explanation)}</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
