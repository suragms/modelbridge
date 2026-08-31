"use client";

import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMarketplaceItem } from "@/lib/hooks";

export default function MarketplaceItemPage() {
  const params = useParams();
  const slug = params.slug as string;
  const { data, isLoading } = useMarketplaceItem(slug);
  const item = data as Record<string, unknown> | undefined;
  const current = item?.current_version as Record<string, unknown> | undefined;
  const versions = (item?.versions as Array<Record<string, unknown>>) ?? [];

  if (isLoading) return <p className="text-sm">Loading...</p>;
  if (!item) return <p className="text-sm">Item not found.</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{String(item.name)}</h1>
        <p className="text-sm text-[var(--muted-foreground)]">{String(item.description ?? "")}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge variant="outline">{String(item.content_type)}</Badge>
          {item.trust_level === "official" && <Badge variant="outline">Official</Badge>}
          {item.publisher_verification === "verified" && <Badge variant="outline">Verified Publisher</Badge>}
          <Badge variant="outline">Security: {String(item.security_review_status)}</Badge>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle className="text-base">Publisher</CardTitle></CardHeader>
          <CardContent className="text-sm">
            <p>{String(item.publisher_name ?? "Unknown")}</p>
            <p className="text-xs text-[var(--muted-foreground)]">@{String(item.publisher_slug ?? "")}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Installs</CardTitle></CardHeader>
          <CardContent className="text-2xl font-semibold">{String(item.install_count ?? 0)}</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Current Version</CardTitle></CardHeader>
          <CardContent className="text-sm">
            {current ? String(current.version) : "—"}
            {current && (
              <p className="text-xs text-[var(--muted-foreground)]">
                Requires ModelBridge {String(current.compatibility_version)}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {current && (
        <Card>
          <CardHeader><CardTitle className="text-base">Permissions</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {((current.permissions as string[]) ?? []).map((p) => (
              <Badge key={p} variant="outline">{p}</Badge>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">Versions</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {versions.map((v) => (
            <div key={String(v.id)} className="flex justify-between rounded border px-3 py-2 text-sm">
              <span>v{String(v.version)}</span>
              <span className="text-xs text-[var(--muted-foreground)]">{String(v.published_at)}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Installation</CardTitle></CardHeader>
        <CardContent className="text-sm text-[var(--muted-foreground)]">
          Install via API: <code>POST /marketplace/items/{"{id}"}/install</code> or CLI:{" "}
          <code>modelbridge marketplace install {slug}</code>
        </CardContent>
      </Card>
    </div>
  );
}
