"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCloudRegions } from "@/lib/hooks";

export default function CloudRegionsPage() {
  const regions = useCloudRegions();
  const regionList = (regions.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Regions</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Region metadata and capabilities. Physical multi-region deployment requires configured infrastructure.
        </p>
      </div>

      <Link href="/cloud" className="text-sm underline">
        ← Cloud
      </Link>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Registered Regions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {regionList.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No regions configured.</p>
          )}
          {regionList.map((r) => (
            <div key={String(r.id)} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <div>
                <span className="font-medium">{String(r.name)}</span>
                <span className="ml-2 text-[var(--muted-foreground)]">({String(r.code)})</span>
              </div>
              <Badge variant="outline">{String(r.status)}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
