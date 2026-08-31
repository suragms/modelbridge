"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCloudHealth, useCloudInstances, useCloudRegions, useCloudRollouts } from "@/lib/hooks";

export default function CloudPage() {
  const health = useCloudHealth();
  const regions = useCloudRegions();
  const instances = useCloudInstances();
  const rollouts = useCloudRollouts();

  const healthData = health.data as Record<string, unknown> | undefined;
  const regionList = (regions.data as Array<Record<string, unknown>>) ?? [];
  const instanceList = (instances.data as Array<Record<string, unknown>>) ?? [];
  const rolloutList = (rollouts.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Cloud Operations</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Platform health, regions, managed instances, and configuration rollouts.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Platform Health</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">{String(healthData?.status ?? "unknown")}</Badge>
            <p className="mt-2 text-xs text-[var(--muted-foreground)]">
              Region: {String(healthData?.deployment_region ?? "local")}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Regions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{regionList.length}</p>
            <Link href="/cloud/regions" className="text-xs underline">
              Manage regions
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Managed Instances</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{instanceList.length}</p>
            <Link href="/cloud/instances" className="text-xs underline">
              View instances
            </Link>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Configuration Rollouts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {rolloutList.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No rollouts recorded.</p>
          )}
          {rolloutList.slice(0, 10).map((r) => (
            <div key={String(r.id)} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <span>v{String(r.configuration_version)}</span>
              <Badge variant="outline">{String(r.status)}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
