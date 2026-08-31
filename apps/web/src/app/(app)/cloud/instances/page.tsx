"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCloudInstances } from "@/lib/hooks";

export default function CloudInstancesPage() {
  const instances = useCloudInstances();
  const instanceList = (instances.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Managed Instances</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Cloud-managed ModelBridge data-plane instances.
        </p>
      </div>

      <Link href="/cloud" className="text-sm underline">
        ← Cloud
      </Link>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Instances</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {instanceList.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No managed instances.</p>
          )}
          {instanceList.map((i) => (
            <Link
              key={String(i.id)}
              href={`/cloud/instances/${i.id}`}
              className="flex items-center justify-between rounded border px-3 py-2 text-sm hover:bg-[var(--muted)]"
            >
              <span>{String(i.name)}</span>
              <div className="flex gap-2">
                <Badge variant="outline">{String(i.lifecycle_status ?? i.status)}</Badge>
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
