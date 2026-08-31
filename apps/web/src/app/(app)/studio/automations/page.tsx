"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAutomations } from "@/lib/hooks";

export default function StudioAutomationsPage() {
  const automations = useAutomations();
  const list = (automations.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Visual Automations</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Built on the Phase 14 automation engine — same triggers, actions, and governance.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Automations</CardTitle>
          <Link href="/automations" className="text-xs underline">
            Full automation view
          </Link>
        </CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No automations configured.</p>
          )}
          {list.map((a) => (
            <div key={String(a.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{String(a.name)}</span>
                <Badge variant="outline">{String(a.status)}</Badge>
              </div>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                {String(a.trigger_type)} → {String(a.action_type)}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
