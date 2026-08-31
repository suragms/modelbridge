"use client";

import Link from "next/link";
import { ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useGovernanceNotifications, useGovernanceOverview } from "@/lib/hooks";

export default function GovernancePage() {
  const overview = useGovernanceOverview();
  const notes = useGovernanceNotifications();
  const data = overview.data as {
    active_policies?: number;
    blocked_requests?: number;
    warnings?: number;
    sensitive_events?: number;
    pending_approvals?: number;
    risk_distribution?: Record<string, number>;
    top_policies?: { name: string; count: number }[];
    recent_events?: Array<Record<string, string | null>>;
  } | undefined;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">AI Governance</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Policy enforcement, detections, and approvals for this organization. Controls are not a
          legal-compliance guarantee.
        </p>
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="underline" href="/governance/policies">
          Policies
        </Link>
        <Link className="underline" href="/governance/approvals">
          Approvals
        </Link>
        <Link className="underline" href="/settings/governance/data-protection">
          Data protection
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ["Active policies", data?.active_policies],
          ["Blocked", data?.blocked_requests],
          ["Warnings", data?.warnings],
          ["Sensitive events", data?.sensitive_events],
          ["Pending approvals", data?.pending_approvals],
        ].map(([label, value]) => (
          <Card key={String(label)}>
            <CardHeader className="pb-2">
              <CardDescription>{label}</CardDescription>
              <CardTitle className="text-2xl">{overview.isLoading ? "…" : (value ?? 0)}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk distribution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(data?.risk_distribution ?? {}).length === 0 && (
              <p className="text-sm text-[var(--muted-foreground)]">No events yet.</p>
            )}
            {Object.entries(data?.risk_distribution ?? {}).map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm">
                <span>{k}</span>
                <span>{v}</span>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Most triggered policies</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(data?.top_policies ?? []).map((p) => (
              <div key={p.name} className="flex justify-between text-sm">
                <span>{p.name}</span>
                <span>{p.count}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">In-app notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {(notes.data ?? []).slice(0, 8).map((n) => (
            <div key={String(n.id)} className="flex items-start gap-2 text-sm">
              <ShieldAlert className="mt-0.5 h-4 w-4" />
              <div>
                <div className="font-medium">{String(n.title)}</div>
                <div className="text-[var(--muted-foreground)]">{String(n.body)}</div>
              </div>
            </div>
          ))}
          {(notes.data ?? []).length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No notifications.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent events</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(data?.recent_events ?? []).map((e) => (
            <div key={String(e.id)} className="flex flex-wrap items-center gap-2 text-sm">
              <Badge>{String(e.event_type)}</Badge>
              <span>{e.reason ?? "—"}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
