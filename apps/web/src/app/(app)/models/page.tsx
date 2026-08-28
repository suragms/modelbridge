"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
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
import type { AIModel } from "@/lib/types";

type CapabilityFilter =
  | "chat"
  | "streaming"
  | "tools"
  | "embeddings"
  | "vision"
  | "json";

const FILTERS: { key: CapabilityFilter; label: string }[] = [
  { key: "chat", label: "Chat" },
  { key: "streaming", label: "Streaming" },
  { key: "tools", label: "Tools" },
  { key: "embeddings", label: "Embeddings" },
  { key: "vision", label: "Vision" },
  { key: "json", label: "JSON" },
];

function modelHasCapability(model: AIModel, cap: CapabilityFilter): boolean {
  switch (cap) {
    case "chat":
      return model.supports_chat !== false && !model.supports_embeddings;
    case "streaming":
      return model.supports_streaming;
    case "tools":
      return model.supports_tools;
    case "embeddings":
      return model.supports_embeddings;
    case "vision":
      return model.supports_vision;
    case "json":
      return model.supports_json_mode || Boolean(model.supports_structured_output);
    default:
      return true;
  }
}

function formatUnknown(value: number | null | undefined, suffix = ""): string {
  if (value == null || value <= 0) return "Unknown";
  return `${value}${suffix}`;
}

export default function ModelsPage() {
  const modelsQuery = useModels();
  const providersQuery = useProviders();
  const [activeFilters, setActiveFilters] = useState<Set<CapabilityFilter>>(new Set());

  const providerName = new Map(
    (providersQuery.data ?? []).map((p) => [p.id, p.name])
  );

  const models = modelsQuery.data ?? [];

  const filteredModels = useMemo(() => {
    if (activeFilters.size === 0) return models;
    return models.filter((m) =>
      [...activeFilters].every((cap) => modelHasCapability(m, cap))
    );
  }, [models, activeFilters]);

  const toggleFilter = (cap: CapabilityFilter) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(cap)) next.delete(cap);
      else next.add(cap);
      return next;
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Models</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Models discovered from your configured providers with capability metadata
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Capability filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => {
              const active = activeFilters.has(f.key);
              return (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => toggleFilter(f.key)}
                  className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                    active
                      ? "border-[var(--ring)] bg-[var(--muted)] text-[var(--foreground)]"
                      : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]/60"
                  }`}
                >
                  {f.label}
                </button>
              );
            })}
            {activeFilters.size > 0 && (
              <button
                type="button"
                className="text-sm text-[var(--ring)] hover:underline"
                onClick={() => setActiveFilters(new Set())}
              >
                Clear filters
              </button>
            )}
          </div>
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">
            Showing {filteredModels.length} of {models.length} models
          </p>
        </CardContent>
      </Card>

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
                <span className="font-medium">Sync Models</span>.
              </p>
              <Link
                href="/providers"
                className="mt-4 inline-block text-sm text-[var(--ring)] hover:underline"
              >
                Go to Providers →
              </Link>
            </div>
          ) : filteredModels.length === 0 ? (
            <p className="py-8 text-center text-[var(--muted-foreground)]">
              No models match the selected capability filters.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Capabilities</TableHead>
                  <TableHead>Context</TableHead>
                  <TableHead>Max output</TableHead>
                  <TableHead className="text-center">Quality</TableHead>
                  <TableHead className="text-right">Latency</TableHead>
                  <TableHead className="text-center">Enabled</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredModels.map((m) => {
                  const caps: { label: string; on: boolean }[] = [
                    { label: "Chat", on: modelHasCapability(m, "chat") },
                    { label: "Streaming", on: m.supports_streaming },
                    { label: "Tools", on: m.supports_tools },
                    { label: "Embeddings", on: m.supports_embeddings },
                    { label: "Vision", on: m.supports_vision },
                    {
                      label: "JSON",
                      on: m.supports_json_mode || Boolean(m.supports_structured_output),
                    },
                  ];
                  return (
                    <TableRow key={m.id}>
                      <TableCell className="font-medium">
                        {m.display_name || m.provider_model_id}
                        <span className="block text-xs text-[var(--muted-foreground)]">
                          {m.provider_model_id}
                        </span>
                        {m.embedding_dimensions != null && m.embedding_dimensions > 0 && (
                          <span className="block text-xs text-[var(--muted-foreground)]">
                            {m.embedding_dimensions} dims
                          </span>
                        )}
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
                      <TableCell className="text-sm">
                        {formatUnknown(m.context_window)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatUnknown(m.max_output_tokens)}
                      </TableCell>
                      <TableCell className="text-center">
                        {m.quality_score != null
                          ? (m.quality_score * 100).toFixed(0)
                          : "—"}
                        <span className="text-xs text-[var(--muted-foreground)]">%</span>
                      </TableCell>
                      <TableCell className="text-right">
                        {m.average_latency_ms != null
                          ? `${Math.round(m.average_latency_ms)}ms`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant={m.is_enabled ? "success" : "secondary"}>
                          {m.is_enabled ? "yes" : "no"}
                        </Badge>
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
