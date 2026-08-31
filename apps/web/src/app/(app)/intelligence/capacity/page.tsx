"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIntelligenceCapacity } from "@/lib/hooks";

export default function CapacityPage() {
  const q = useIntelligenceCapacity();
  const data = q.data as Record<string, unknown> | undefined;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Capacity Intelligence</h1>
      <Link href="/intelligence" className="text-sm underline">← Intelligence</Link>
      <Card>
        <CardHeader><CardTitle className="text-base">Current Load</CardTitle></CardHeader>
        <CardContent className="text-sm space-y-2">
          <div className="flex justify-between"><span>Health</span><Badge variant="outline">{String(data?.capacity_health)}</Badge></div>
          <p>Daily requests (current): {String(data?.current_daily_requests)}</p>
          <p>Daily requests (average): {String(data?.average_daily_requests)}</p>
          <p className="text-xs text-[var(--muted-foreground)]">{String(data?.disclaimer ?? "")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
