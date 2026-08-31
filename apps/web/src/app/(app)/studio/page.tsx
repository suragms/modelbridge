"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStudioOverview } from "@/lib/hooks";

const SECTIONS = [
  { href: "/studio/workflows", label: "Workflows", key: "workflows" },
  { href: "/studio/agents", label: "Agents", key: "agents" },
  { href: "/studio/prompts", label: "Prompts", key: "prompts" },
  { href: "/studio/evaluations", label: "Evaluations", key: "evaluations" },
  { href: "/studio/deployments", label: "Deployments", key: "deployments" },
];

export default function StudioHomePage() {
  const overview = useStudioOverview();
  const data = overview.data as Record<string, unknown> | undefined;
  const activity = (data?.recent_activity as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">AI Studio</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Build, test, evaluate, and deploy AI systems through a visual interface.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-5">
        {SECTIONS.map((section) => (
          <Link key={section.href} href={section.href}>
            <Card className="transition-colors hover:bg-[var(--muted)]/40">
              <CardHeader>
                <CardTitle className="text-base">{section.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{String(data?.[section.key] ?? 0)}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/studio/playground" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">
          Prompt Playground
        </Link>
        <Link href="/studio/automations" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">
          Visual Automations
        </Link>
        <Link href="/marketplace" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">
          Studio Templates
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {activity.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No recent studio activity.</p>
          )}
          {activity.map((item, i) => (
            <div key={i} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <span>
                {String(item.resource_type)} v{String(item.version)} — {String(item.summary ?? "")}
              </span>
              <Badge variant="outline">{String(item.timestamp ?? "").slice(0, 10)}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
