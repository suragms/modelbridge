"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useExtensionInstallations, useExtensionPackages } from "@/lib/hooks";

export default function ExtensionsPage() {
  const installations = useExtensionInstallations();
  const packages = useExtensionPackages();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Extensions</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Installed extensions, permissions, and health. Review before enabling in production.
        </p>
      </div>

      <div className="flex gap-3 text-sm">
        <Link className="underline" href="/templates">
          Template gallery
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Installed extensions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(installations.data ?? []).length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No extensions installed.</p>
          )}
          {(installations.data ?? []).map((e) => (
            <Link
              key={String(e.id)}
              href={`/extensions/${e.id}`}
              className="flex items-center justify-between rounded-md border px-3 py-2 text-sm hover:bg-[var(--muted)]"
            >
              <span>
                {String(e.package_display_name ?? e.package_name ?? e.id)}
                <span className="ml-2 text-xs text-[var(--muted-foreground)]">v{String(e.version)}</span>
              </span>
              <div className="flex gap-2">
                <Badge variant="outline">{String(e.status)}</Badge>
                <Badge variant="outline">{String(e.health_status)}</Badge>
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Available packages</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(packages.data ?? []).map((p) => (
            <div key={String(p.id)} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
              <span>{String(p.display_name)}</span>
              <div className="flex gap-2">
                <Badge variant="outline">{String(p.plugin_type)}</Badge>
                <Badge variant="outline">{String(p.trust_level)}</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
