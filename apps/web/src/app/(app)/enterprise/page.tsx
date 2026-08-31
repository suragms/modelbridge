"use client";

import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useEnterpriseOverview, useWorkspaces } from "@/lib/hooks";

export default function EnterprisePage() {
  const overview = useEnterpriseOverview();
  const workspaces = useWorkspaces();
  const data = overview.data as Record<string, number> | undefined;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Enterprise Administration</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Workspaces, projects, fleet health, and centralized control-plane overview.
        </p>
      </div>

      <div className="flex gap-3 text-sm">
        <Link className="underline" href="/fleet">
          Fleet
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Workspaces", data?.workspaces],
          ["Projects", data?.projects],
          ["Environments", data?.environments],
          ["Instances", data?.instances],
          ["Healthy instances", data?.healthy_instances],
          ["Recent deployments", data?.recent_deployments],
        ].map(([label, value]) => (
          <Card key={String(label)}>
            <CardHeader className="pb-2">
              <CardDescription>{label}</CardDescription>
              <CardTitle className="text-2xl">{overview.isLoading ? "…" : (value ?? 0)}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Workspaces</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(workspaces.data ?? []).map((w) => (
            <Link
              key={String(w.id)}
              href={`/workspaces/${w.id}`}
              className="flex justify-between rounded border px-3 py-2 text-sm hover:bg-[var(--muted)]"
            >
              <span>{String(w.name)}</span>
              <span className="text-xs text-[var(--muted-foreground)]">{String(w.project_count ?? 0)} projects</span>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
