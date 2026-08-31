"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useExtensionInstallation } from "@/lib/hooks";

export default function ExtensionDetailPage() {
  const params = useParams();
  const id = String(params.id);
  const ext = useExtensionInstallation(id);
  const data = ext.data as Record<string, unknown> | undefined;

  if (ext.isLoading) return <p className="text-sm">Loading…</p>;
  if (!data) return <p className="text-sm">Extension not found.</p>;

  const perms = (data.permissions as string[]) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <Link href="/extensions" className="text-sm underline">
          ← Extensions
        </Link>
        <h1 className="mt-2 text-2xl font-bold">{String(data.package_display_name ?? data.package_name)}</h1>
        <div className="mt-2 flex gap-2">
          <Badge variant="outline">{String(data.status)}</Badge>
          <Badge variant="outline">{String(data.trust_level)}</Badge>
          <Badge variant="outline">{String(data.health_status)}</Badge>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Version: {String(data.version)}</p>
          <p>Type: {String(data.plugin_type)}</p>
          <p>Executions: {String(data.execution_count)}</p>
          <p>Failures: {String(data.failure_count)}</p>
          {data.last_error != null && <p className="text-red-600">{String(data.last_error)}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Permissions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {perms.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No permissions declared.</p>}
          {perms.map((p) => (
            <Badge key={p} variant="outline">
              {p}
            </Badge>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
