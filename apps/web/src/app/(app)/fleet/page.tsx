"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFleet } from "@/lib/hooks";

export default function FleetPage() {
  const fleet = useFleet();
  const data = fleet.data as { instances?: Array<Record<string, unknown>>; by_status?: Record<string, number> } | undefined;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Fleet Management</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Registered ModelBridge instances, health, and versions.
        </p>
      </div>

      <Link href="/enterprise" className="text-sm underline">
        ← Enterprise
      </Link>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Instances</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(data?.instances ?? []).length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No instances registered.</p>
          )}
          {(data?.instances ?? []).map((i) => (
            <Link
              key={String(i.id)}
              href={`/fleet/${i.id}`}
              className="flex items-center justify-between rounded border px-3 py-2 text-sm hover:bg-[var(--muted)]"
            >
              <span>{String(i.name)}</span>
              <Badge variant="outline">{String(i.status)}</Badge>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
