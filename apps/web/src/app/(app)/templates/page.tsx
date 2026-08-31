"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTemplates } from "@/lib/hooks";

export default function TemplatesPage() {
  const templates = useTemplates();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Template Gallery</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Official, verified, and community agent and workflow templates. Trust labels indicate source — not safety guarantees.
        </p>
      </div>

      <Link href="/extensions" className="text-sm underline">
        Manage extensions
      </Link>

      <div className="grid gap-4 md:grid-cols-2">
        {(templates.data ?? []).map((t) => (
          <Card key={String(t.id)}>
            <CardHeader>
              <CardTitle className="text-base">{String(t.display_name)}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>{String(t.description ?? "")}</p>
              <div className="flex gap-2">
                <Badge variant="outline">{String(t.plugin_type)}</Badge>
                <Badge variant="outline">{String(t.trust_level)}</Badge>
                {t.category != null && <Badge variant="outline">{String(t.category)}</Badge>}
              </div>
              <p className="text-xs text-[var(--muted-foreground)]">
                Install the package from Extensions, enable it, then apply via API or CLI.
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
