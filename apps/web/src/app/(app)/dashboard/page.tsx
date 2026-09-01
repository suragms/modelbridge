"use client";

import Link from "next/link";
import { Activity, BarChart3, DollarSign, Timer, TrendingUp, Zap, ArrowUpRight, ArrowDownRight, ChevronRight, Server, AlertCircle } from "lucide-react";

import { TimeSeriesChart } from "@/components/charts/time-series-chart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useAnalyticsCost,
  useAnalyticsErrors,
  useAnalyticsOverview,
  useAnalyticsProviders,
  useAnalyticsRequests,
  useAnalyticsTokens,
  useHealth,
  useProviders,
} from "@/lib/hooks";

const STAT_CARDS = [
  {
    key: "requests",
    label: "Total Requests",
    icon: Activity,
    gradient: "from-blue-500 to-cyan-400",
    getValue: (ov: any) => ov?.total_requests ?? 0,
    format: (v: number) => v.toLocaleString(),
    suffix: undefined as string | undefined,
  },
  {
    key: "success",
    label: "Success Rate",
    icon: TrendingUp,
    gradient: "from-emerald-500 to-green-400",
    getValue: (ov: any) => ov?.success_rate ?? 0,
    format: (v: number) => `${v}%`,
    suffix: undefined,
  },
  {
    key: "tokens",
    label: "Total Tokens",
    icon: Zap,
    gradient: "from-violet-500 to-purple-400",
    getValue: (ov: any) => ov?.total_tokens ?? 0,
    format: (v: number) => v.toLocaleString(),
    suffix: undefined,
  },
  {
    key: "cost",
    label: "Est. Cost",
    icon: DollarSign,
    gradient: "from-amber-500 to-orange-400",
    getValue: (ov: any) => ov?.estimated_total_cost ?? 0,
    format: (v: number) => `$${v.toFixed(4)}`,
    suffix: "est.",
  },
  {
    key: "latency",
    label: "Avg Latency",
    icon: Timer,
    gradient: "from-rose-500 to-pink-400",
    getValue: (ov: any) => ov?.average_latency_ms ?? 0,
    format: (v: number) => `${v.toFixed(0)}ms`,
    suffix: undefined,
  },
];

export default function DashboardPage() {
  const overview = useAnalyticsOverview();
  const requests = useAnalyticsRequests();
  const tokens = useAnalyticsTokens();
  const cost = useAnalyticsCost();
  const providers = useAnalyticsProviders();
  const errors = useAnalyticsErrors({ start: undefined, end: undefined });
  const healthQuery = useHealth();
  const providersQuery = useProviders();

  const ov = overview.data;
  const hasData = ov?.has_data ?? false;
  const systemStatus = healthQuery.data?.status ?? "unknown";

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            Analytics console powered by real gateway traffic
          </p>
        </div>
        {hasData && (
          <Badge variant="success" className="gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            Live
          </Badge>
        )}
      </div>

      {!hasData && !overview.isLoading ? (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand-gradient-soft)]">
              <Activity className="h-6 w-6 text-[var(--primary)]" />
            </div>
            <h3 className="text-lg font-semibold">No request data yet</h3>
            <p className="mx-auto mt-2 max-w-sm text-sm text-[var(--muted-foreground)]">
              Route your first request through{" "}
              <code className="rounded bg-[var(--muted)] px-1.5 py-0.5 text-xs font-mono">/v1/chat/completions</code>{" "}
              to see analytics here.
            </p>
            <Link href="/providers" className="mt-6 inline-block">
              <Button variant="outline" className="gap-2">
                Add a provider <ChevronRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5 stagger-children">
            {STAT_CARDS.map((stat) => {
              const Icon = stat.icon;
              const value = overview.isLoading ? null : stat.getValue(ov);
              return (
                <div
                  key={stat.key}
                  className="card-interactive group p-5"
                >
                  <div className="flex items-center justify-between">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${stat.gradient} shadow-sm transition-transform duration-200 group-hover:scale-110`}>
                      <Icon className="h-4 w-4 text-white" />
                    </div>
                    {stat.suffix && (
                      <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                        {stat.suffix}
                      </span>
                    )}
                  </div>
                  <div className="mt-4">
                    <p className="text-2xl font-bold tracking-tight">
                      {value === null ? (
                        <span className="inline-block h-7 w-20 animate-pulse rounded-md bg-[var(--muted)]" />
                      ) : (
                        stat.format(value)
                      )}
                    </p>
                    <p className="mt-1 text-xs font-medium text-[var(--muted-foreground)]">
                      {stat.label}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Charts row */}
          <div className="grid gap-5 lg:grid-cols-2">
            <Card className="overflow-hidden">
              <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30">
                <CardTitle className="text-sm font-semibold">Requests Over Time</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <TimeSeriesChart data={requests.data?.data ?? []} label="Requests" />
              </CardContent>
            </Card>
            <Card className="overflow-hidden">
              <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30">
                <CardTitle className="text-sm font-semibold">Tokens Over Time</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <TimeSeriesChart data={tokens.data?.data ?? []} label="Tokens" />
              </CardContent>
            </Card>
            <Card className="overflow-hidden">
              <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30">
                <CardTitle className="text-sm font-semibold">Estimated Cost Over Time</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <TimeSeriesChart
                  data={cost.data?.data ?? []}
                  label="Cost (USD, estimated)"
                  valueFormatter={(v) => `$${v.toFixed(4)}`}
                />
              </CardContent>
            </Card>

            {/* System status card */}
            <Card className="overflow-hidden">
              <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                  <Server className="h-4 w-4" /> System Status
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-4">
                  {/* Status indicator */}
                  <div className="flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--muted)]/20 px-4 py-3">
                    <span className="text-sm font-medium">Gateway Status</span>
                    <Badge variant={systemStatus === "healthy" ? "success" : "warning"} className="gap-1.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${systemStatus === "healthy" ? "bg-emerald-500" : "bg-amber-500"} animate-pulse`} />
                      {systemStatus}
                    </Badge>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 p-3 text-center">
                      <p className="text-2xl font-bold">{providersQuery.data?.filter((p) => p.is_enabled).length ?? "—"}</p>
                      <p className="mt-1 text-xs text-[var(--muted-foreground)]">Active Providers</p>
                    </div>
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 p-3 text-center">
                      <p className="text-2xl font-bold">{ov?.active_providers ?? "—"}</p>
                      <p className="mt-1 text-xs text-[var(--muted-foreground)]">Providers w/ Traffic</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Bottom tables */}
          <div className="grid gap-5 lg:grid-cols-2">
            <Card className="overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between border-b border-[var(--border)] bg-[var(--muted)]/30">
                <CardTitle className="text-sm font-semibold">Top Providers</CardTitle>
                <Link href="/analytics" className="text-xs text-[var(--primary)] hover:underline">
                  View all
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                {(providers.data?.breakdown ?? []).length === 0 ? (
                  <div className="p-6 text-center text-sm text-[var(--muted-foreground)]">
                    No provider data yet.
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead>Provider</TableHead>
                        <TableHead className="text-right">Requests</TableHead>
                        <TableHead className="text-right">Success</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(providers.data?.breakdown ?? []).slice(0, 5).map((p) => (
                        <TableRow key={p.provider} className="group">
                          <TableCell className="font-medium">
                            <span className="inline-flex items-center gap-2">
                              <span className="h-2 w-2 rounded-full bg-[var(--primary)]" />
                              {p.provider}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">{p.total_requests}</TableCell>
                          <TableCell className="text-right">
                            <Badge variant={Number(p.success_rate) >= 95 ? "success" : "warning"}>
                              {p.success_rate}%
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            <Card className="overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between border-b border-[var(--border)] bg-[var(--muted)]/30">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                  <AlertCircle className="h-4 w-4 text-red-500" /> Recent Errors
                </CardTitle>
                <Link href="/requests" className="text-xs text-[var(--primary)] hover:underline">
                  View all
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                {(errors.data?.errors ?? []).length === 0 ? (
                  <div className="p-6 text-center text-sm text-[var(--muted-foreground)]">
                    <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/20">
                      <TrendingUp className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    No recent errors. Everything looks good!
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead>Type</TableHead>
                        <TableHead>Provider</TableHead>
                        <TableHead>Message</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(errors.data?.errors ?? []).slice(0, 5).map((e) => (
                        <TableRow key={e.request_id}>
                          <TableCell>
                            <Badge variant="destructive">{e.error_type}</Badge>
                          </TableCell>
                          <TableCell>{e.provider}</TableCell>
                          <TableCell className="max-w-xs truncate text-[var(--muted-foreground)]">
                            {e.message}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
