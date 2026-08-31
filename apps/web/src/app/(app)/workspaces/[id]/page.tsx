"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useProjects, useWorkspace } from "@/lib/hooks";

export default function WorkspacePage() {
  const params = useParams();
  const id = String(params.id);
  const ws = useWorkspace(id);
  const projects = useProjects(id);
  const data = ws.data as Record<string, unknown> | undefined;

  if (ws.isLoading) return <p className="text-sm">Loading…</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/enterprise" className="text-sm underline">
          ← Enterprise
        </Link>
        <h1 className="mt-2 text-2xl font-bold">{String(data?.name ?? "Workspace")}</h1>
        <p className="text-sm text-[var(--muted-foreground)]">{String(data?.description ?? "")}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Projects</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(projects.data ?? []).map((p) => (
            <Link
              key={String(p.id)}
              href={`/projects/${p.id}`}
              className="block rounded border px-3 py-2 text-sm hover:bg-[var(--muted)]"
            >
              {String(p.name)}
              {p.is_restricted ? " · restricted" : ""}
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
