"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useGovernancePolicy, useSimulatePolicy } from "@/lib/hooks";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function PolicyDetailPage() {
  const params = useParams<{ id: string }>();
  const policyQuery = useGovernancePolicy(params.id);
  const simulate = useSimulatePolicy();
  const { token, activeOrgId, user } = useAuth();
  const orgId = activeOrgId ?? user?.organization_id ?? null;
  const [prompt, setPrompt] = useState("Hello");
  const [versions, setVersions] = useState<Array<Record<string, unknown>>>([]);
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const p = policyQuery.data;

  const loadExtra = async () => {
    if (!token || !params.id) return;
    const v = await api.get<Array<Record<string, unknown>>>(
      `/governance/policies/${params.id}/versions`,
      token,
      orgId
    );
    const e = await api.get<Array<Record<string, unknown>>>(
      `/governance/policies/${params.id}/events`,
      token,
      orgId
    );
    setVersions(v);
    setEvents(e);
  };

  if (p && versions.length === 0) {
    void loadExtra();
  }

  return (
    <div className="space-y-8">
      <Link href="/governance/policies" className="text-sm underline">
        ← Policies
      </Link>
      <div>
        <h1 className="text-2xl font-bold">{p ? String(p.name) : "Policy"}</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          {p ? `${p.policy_type} · ${p.action} · ${p.status} · priority ${p.priority}` : ""}
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Definition</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="overflow-auto rounded bg-[var(--muted)] p-3 text-xs">
            {JSON.stringify(p?.rules ?? {}, null, 2)}
          </pre>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Simulation (no provider call)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            className="min-h-24 w-full rounded-md border border-[var(--border)] p-2 text-sm"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <Button
            onClick={() =>
              simulate.mutate({
                model: "auto",
                messages: [{ role: "user", content: prompt }],
              })
            }
          >
            Simulate
          </Button>
          {simulate.data && (
            <pre className="overflow-auto rounded bg-[var(--muted)] p-3 text-xs">
              {JSON.stringify(simulate.data, null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Version history</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {versions.map((v) => (
            <div key={String(v.id)}>
              v{String(v.version)} · {String(v.changed_at)} · {String(v.change_summary ?? "")}
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent matches</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {events.map((e) => (
            <div key={String(e.id)}>
              {String(e.event_type)} · {String(e.decision ?? "")} · {String(e.reason ?? "")}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
