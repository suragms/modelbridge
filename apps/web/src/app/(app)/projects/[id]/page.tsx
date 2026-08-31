"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEnvironments, useProject } from "@/lib/hooks";

export default function ProjectPage() {
  const params = useParams();
  const id = String(params.id);
  const project = useProject(id);
  const envs = useEnvironments(id);
  const data = project.data as Record<string, unknown> | undefined;

  if (project.isLoading) return <p className="text-sm">Loading…</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/workspaces/${data?.workspace_id}`} className="text-sm underline">
          ← Workspace
        </Link>
        <h1 className="mt-2 text-2xl font-bold">{String(data?.name)}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Environments</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(envs.data ?? []).map((e) => (
            <Link
              key={String(e.id)}
              href={`/projects/${id}/environments/${e.slug}`}
              className="flex justify-between rounded border px-3 py-2 text-sm hover:bg-[var(--muted)]"
            >
              <span>{String(e.name)}</span>
              <span className="text-xs text-[var(--muted-foreground)]">
                v{String(e.active_config_version ?? "—")}
              </span>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
