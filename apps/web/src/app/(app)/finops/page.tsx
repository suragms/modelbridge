"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFinopsOverview } from "@/lib/hooks";

export default function FinopsHomePage() {
  const overview = useFinopsOverview();
  const data = overview.data as Record<string, unknown> | undefined;
  const drivers = (data?.top_cost_drivers as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">AI FinOps</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Unified cost tracking, budgets, forecasting, and optimization — all costs clearly labeled.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Current Spend</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">${Number(data?.current_spend ?? 0).toFixed(4)}</p>
            <Badge variant="outline" className="mt-1">{String(data?.cost_type ?? "unknown")}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Active Budgets</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-semibold">{String(data?.active_budgets ?? 0)}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Forecast</CardTitle></CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">
              {data?.forecast_amount != null ? `$${Number(data.forecast_amount).toFixed(2)}` : "—"}
            </p>
            <p className="text-xs text-[var(--muted-foreground)]">estimated</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Optimizations</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-semibold">{String(data?.optimization_count ?? 0)}</p></CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/finops/explorer" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Cost Explorer</Link>
        <Link href="/finops/budgets" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Budgets</Link>
        <Link href="/finops/forecast" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Forecast</Link>
        <Link href="/finops/anomalies" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Anomalies</Link>
        <Link href="/finops/optimization" className="rounded border p-4 text-sm hover:bg-[var(--muted)]">Optimization</Link>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Top Cost Drivers</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {drivers.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No cost data yet.</p>}
          {drivers.map((d) => (
            <div key={String(d.model)} className="flex justify-between rounded border px-3 py-2 text-sm">
              <span>{String(d.model)}</span>
              <span>${Number(d.cost ?? 0).toFixed(4)}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
