"use client";

import Link from "next/link";
import { Boxes } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useModels, useProviders } from "@/lib/hooks";

export default function ModelsPage() {
  const modelsQuery = useModels();
  const providersQuery = useProviders();

  const providerName = new Map(
    (providersQuery.data ?? []).map((p) => [p.id, p.name])
  );

  const models = modelsQuery.data ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Models</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Models discovered from your configured providers
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Available Models</CardTitle>
        </CardHeader>
        <CardContent>
          {modelsQuery.isLoading ? (
            <p className="py-8 text-center text-[var(--muted-foreground)]">Loading…</p>
          ) : models.length === 0 ? (
            <div className="py-12 text-center">
              <Boxes className="mx-auto h-8 w-8 text-[var(--muted-foreground)]" />
              <p className="mt-3 text-[var(--muted-foreground)]">
                No models discovered yet. Connect a provider and run{" "}
                <span className="font-medium">Discover Models</span>.
              </p>
              <Link
                href="/providers"
                className="mt-4 inline-block text-sm text-[var(--ring)] hover:underline"
              >
                Go to Providers →
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Capabilities</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {models.map((m) => {
                  const caps: { label: string; on: boolean }[] = [
                    { label: "Chat", on: true },
                    { label: "Streaming", on: m.supports_streaming },
                    { label: "Tools", on: m.supports_tools },
                    { label: "Embeddings", on: m.supports_embeddings },
                    { label: "Vision", on: m.supports_vision },
                    { label: "JSON", on: m.supports_json_mode },
                  ];
                  return (
                    <TableRow key={m.id}>
                      <TableCell className="font-medium">
                        {m.display_name || m.provider_model_id}
                      </TableCell>
                      <TableCell>
                        {providerName.get(m.provider_id) ?? m.provider_id.slice(0, 8)}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {caps
                            .filter((c) => c.on)
                            .map((c) => (
                              <Badge key={c.label} variant="secondary">
                                {c.label}
                              </Badge>
                            ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
