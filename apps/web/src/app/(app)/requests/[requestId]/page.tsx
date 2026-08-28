"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useParams } from "next/navigation";
import { Activity, ArrowLeft, Clock, DollarSign, Route, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRequestDetail } from "@/lib/hooks";

function statusVariant(status: string) {
  if (status === "COMPLETED" || status === "success") return "success" as const;
  if (status === "FAILED" || status === "error") return "destructive" as const;
  return "secondary" as const;
}

export default function RequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const requestId = params.requestId as string;
  const detailQuery = useRequestDetail(requestId);
  const log = detailQuery.data;

  if (detailQuery.isLoading) {
    return <p className="py-12 text-center text-[var(--muted-foreground)]">Loading…</p>;
  }

  if (!log) {
    return (
      <div className="py-12 text-center">
        <p className="text-[var(--muted-foreground)]">Request not found.</p>
        <Link href="/requests" className="mt-4 inline-block text-sm text-[var(--ring)] hover:underline">
          ← Back to requests
        </Link>
      </div>
    );
  }

  const duration =
    log.completed_at && log.created_at
      ? new Date(log.completed_at).getTime() - new Date(log.created_at).getTime()
      : log.latency_ms;

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/requests")}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Back
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Request Detail</h1>
          <p className="font-mono text-sm text-[var(--muted-foreground)]">{log.request_id}</p>
        </div>
        <Badge variant={statusVariant(log.status)} className="ml-auto">
          {log.status}
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4" /> Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Created" value={new Date(log.created_at).toLocaleString()} />
            <Row label="Completed" value={log.completed_at ? new Date(log.completed_at).toLocaleString() : "—"} />
            <Row label="Duration" value={`${duration.toFixed(0)} ms`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Route className="h-4 w-4" /> Routing
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Requested Model" value={log.requested_model ?? log.model} />
            <Row label="Selected Model" value={log.selected_model ?? log.model} />
            <Row label="Provider" value={log.provider} />
            <Row label="Strategy" value={log.routing_strategy ?? "—"} />
            <Row label="Fallback Count" value={String(log.fallback_count ?? 0)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4" /> Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Input Tokens" value={log.input_tokens != null ? String(log.input_tokens) : "—"} />
            <Row label="Output Tokens" value={log.output_tokens != null ? String(log.output_tokens) : "—"} />
            <Row label="Total Tokens" value={log.total_tokens != null ? String(log.total_tokens) : "—"} />
            <Row label="Usage Source" value={log.usage_source ?? "UNAVAILABLE"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <DollarSign className="h-4 w-4" /> Cost (Estimated)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-xs text-[var(--muted-foreground)]">{log.cost_disclaimer}</p>
            <Row label="Input Cost" value={formatCost(log.estimated_input_cost)} />
            <Row label="Output Cost" value={formatCost(log.estimated_output_cost)} />
            <Row label="Total Cost" value={formatCost(log.estimated_total_cost)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4" /> Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Total Latency" value={`${log.latency_ms.toFixed(0)} ms`} />
            <Row
              label="Provider Latency"
              value={log.provider_latency_ms != null ? `${log.provider_latency_ms.toFixed(0)} ms` : "—"}
            />
          </CardContent>
        </Card>

        {(log.error || log.error_type) && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base text-red-600">Error</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Row label="Type" value={log.error_type ?? "—"} />
              <Row label="Code" value={log.error_code ?? "—"} />
              {log.error && (
                <p className="rounded-md bg-red-50 p-2 text-red-700 dark:bg-red-950/30">{log.error}</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-[var(--border)] py-1 last:border-0">
      <span className="text-[var(--muted-foreground)]">{label}</span>
      <span className="max-w-[60%] truncate text-right font-medium" title={value}>
        {value}
      </span>
    </div>
  );
}

function formatCost(v: number | null | undefined): string {
  if (v == null) return "Unknown";
  if (v === 0) return "$0.00 (est.)";
  return `$${v.toFixed(6)} (est.)`;
}
