"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEnvironments } from "@/lib/hooks";

export default function EnvironmentPage() {
  const params = useParams();
  const projectId = String(params.id);
  const slug = String(params.environment);
  const envs = useEnvironments(projectId);
  const env = (envs.data ?? []).find((e) => String(e.slug) === slug);

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/projects/${projectId}`} className="text-sm underline">
          ← Project
        </Link>
        <h1 className="mt-2 text-2xl font-bold">{String(env?.name ?? slug)}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Kind: {String(env?.kind ?? "—")}</p>
          <p>Active version: {String(env?.active_config_version ?? "none")}</p>
          <p className="text-[var(--muted-foreground)]">
            Secret references are stored separately and never displayed here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
