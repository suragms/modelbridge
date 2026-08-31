"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDeveloperOverview, useEventCatalog } from "@/lib/hooks";

export default function DevelopersPage() {
  const overview = useDeveloperOverview();
  const catalog = useEventCatalog();

  const data = overview.data as Record<string, unknown> | undefined;
  const events = (catalog.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Developer Portal</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Events, webhooks, integrations, automations, and API documentation.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Event Types</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-semibold">{String(data?.event_types ?? 0)}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Webhooks</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{String(data?.webhooks ?? 0)}</p>
            <Link href="/webhooks" className="text-xs underline">Manage</Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Integrations</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{String(data?.integrations ?? 0)}</p>
            <Link href="/integrations" className="text-xs underline">Manage</Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Automations</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{String(data?.automations ?? 0)}</p>
            <Link href="/automations" className="text-xs underline">Manage</Link>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Getting Started</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>Authenticate with a Bearer token or scoped API key.</p>
            <p>Interactive API docs: <a href="/docs" className="underline" target="_blank" rel="noreferrer">OpenAPI /docs</a></p>
            <p>SDKs: Python (<code>modelbridge</code>) and TypeScript (<code>@modelbridge/sdk</code>)</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Webhook Signing</CardTitle></CardHeader>
          <CardContent className="text-sm text-[var(--muted-foreground)]">
            Outbound webhooks include <code>X-ModelBridge-Signature</code> using HMAC-SHA256:
            <code className="mt-2 block rounded bg-[var(--muted)] p-2 text-xs">t=timestamp,v1=hex_hmac</code>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Event Catalog</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {events.slice(0, 12).map((e) => (
            <div key={String(e.type)} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <span className="font-mono">{String(e.type)}</span>
              <Badge variant="outline">{String(e.category)}</Badge>
            </div>
          ))}
          {events.length > 12 && (
            <p className="text-xs text-[var(--muted-foreground)]">+ {events.length - 12} more event types</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
