"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCloudInstance } from "@/lib/hooks";

export default function CloudInstanceDetailPage() {
  const params = useParams();
  const id = String(params.id);
  const instance = useCloudInstance(id);
  const data = instance.data as Record<string, unknown> | undefined;

  if (!data && !instance.isLoading) {
    return (
      <div className="space-y-4">
        <Link href="/cloud/instances" className="text-sm underline">
          ← Instances
        </Link>
        <p className="text-sm text-[var(--muted-foreground)]">Instance not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">{String(data?.name ?? "Instance")}</h1>
        <p className="text-sm text-[var(--muted-foreground)]">{String(data?.endpoint ?? "")}</p>
      </div>

      <Link href="/cloud/instances" className="text-sm underline">
        ← Instances
      </Link>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Health</span>
              <Badge variant="outline">{String(data?.status)}</Badge>
            </div>
            <div className="flex justify-between">
              <span>Lifecycle</span>
              <Badge variant="outline">{String(data?.lifecycle_status ?? "unknown")}</Badge>
            </div>
            <div className="flex justify-between">
              <span>Plane</span>
              <span>{String(data?.plane_type ?? "data")}</span>
            </div>
            <div className="flex justify-between">
              <span>Version</span>
              <span>{String(data?.version ?? "—")}</span>
            </div>
            <div className="flex justify-between">
              <span>Last seen</span>
              <span>{data?.last_seen_at ? String(data.last_seen_at) : "—"}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-[var(--muted-foreground)]">
            <p>Region ID: {data?.region_id ? String(data.region_id) : "Not assigned"}</p>
            <p className="mt-2">Environment: {String(data?.environment_kind ?? "—")}</p>
            <p className="mt-4 text-xs">
              Credentials are never displayed. Use the provisioning API to rotate instance credentials.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
