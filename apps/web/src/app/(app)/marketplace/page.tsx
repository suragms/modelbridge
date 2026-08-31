"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMarketplaceDiscovery, useMarketplaceItems } from "@/lib/hooks";

export default function MarketplacePage() {
  const discovery = useMarketplaceDiscovery();
  const items = useMarketplaceItems();
  const data = discovery.data as Record<string, unknown> | undefined;
  const featured = (data?.featured as Array<Record<string, unknown>>) ?? [];
  const official = (data?.official as Array<Record<string, unknown>>) ?? [];
  const popular = (data?.popular as Array<Record<string, unknown>>) ?? [];
  const categories = (data?.categories as string[]) ?? [];
  const all = (items.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Marketplace</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Discover extensions, agents, workflows, integrations, and templates from official and community publishers.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {categories.map((c) => (
          <Badge key={c} variant="outline">{c.replace(/_/g, " ")}</Badge>
        ))}
      </div>

      <Section title="Featured" items={featured} />
      <Section title="Official" items={official} />
      <Section title="Popular" subtitle="Ranked by real install counts" items={popular} />
      <Section title="All Items" items={all} />
    </div>
  );
}

function Section({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle?: string;
  items: Array<Record<string, unknown>>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {subtitle && <p className="text-xs text-[var(--muted-foreground)]">{subtitle}</p>}
      </CardHeader>
      <CardContent className="space-y-2">
        {items.length === 0 && (
          <p className="text-sm text-[var(--muted-foreground)]">No items yet.</p>
        )}
        {items.map((item) => (
          <Link
            key={String(item.id)}
            href={`/marketplace/${String(item.slug)}`}
            className="flex items-center justify-between rounded border px-3 py-2 text-sm hover:bg-[var(--muted)]"
          >
            <div>
              <span className="font-medium">{String(item.name)}</span>
              <span className="ml-2 text-xs text-[var(--muted-foreground)]">{String(item.content_type)}</span>
            </div>
            <div className="flex items-center gap-2">
              {Boolean(item.featured) && <Badge variant="outline">Featured</Badge>}
              {item.trust_level === "official" && <Badge variant="outline">Official</Badge>}
              <Badge variant="outline">{String(item.status)}</Badge>
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
