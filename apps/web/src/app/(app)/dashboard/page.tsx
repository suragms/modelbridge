"use client";

import Link from "next/link";
import { Activity, BarChart3, DollarSign, Timer, TrendingUp, Zap } from "lucide-react";

import { TimeSeriesChart } from "@/components/charts/time-series-chart";
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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Analytics console powered by real gateway traffic
        </p>
      </div>

      {!hasData && !overview.isLoading ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-[var(--muted-foreground)]">
              No request data available yet. Route your first request through{" "}
              <code className="rounded bg-[var(--muted)] px-1">/v1/chat/completions</code>.
            </p>
            <Link href="/providers" className="mt-4 inline-block text-sm text-[var(--ring)] hover:underline">
              Add a provider →
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">Requests</CardTitle>
                <Activity className="h-4 w-4 text-[var(--muted-foreground)]" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{overview.isLoading ? "—" : ov?.total_requests ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">Success Rate</CardTitle>
                <TrendingUp className="h-4 w-4 text-[var(--muted-foreground)]" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {overview.isLoading ? "—" : `${ov?.success_rate ?? 0}%`}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">Total Tokens</CardTitle>
                <Zap className="h-4 w-4 text-[var(--muted-foreground)]" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{overview.isLoading ? "—" : ov?.total_tokens ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">Est. Cost</CardTitle>
                <DollarSign className="h-4 w-4 text-[var(--muted-foreground)]" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {overview.isLoading ? "—" : `$${(ov?.estimated_total_cost ?? 0).toFixed(4)}`}
                </p>
                <p className="text-xs text-[var(--muted-foreground)]">Estimated, not exact billing</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">Avg Latency</CardTitle>
                <Timer className="h-4 w-4 text-[var(--muted-foreground)]" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {overview.isLoading ? "—" : `${(ov?.average_latency_ms ?? 0).toFixed(0)}ms`}
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Requests Over Time</CardTitle></CardHeader>
              <CardContent>
                <TimeSeriesChart data={requests.data?.data ?? []} label="Requests" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Tokens Over Time</CardTitle></CardHeader>
              <CardContent>
                <TimeSeriesChart data={tokens.data?.data ?? []} label="Tokens" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Estimated Cost Over Time</CardTitle></CardHeader>
              <CardContent>
                <TimeSeriesChart
                  data={cost.data?.data ?? []}
                  label="Cost (USD, estimated)"
                  valueFormatter={(v) => `$${v.toFixed(4)}`}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-4 w-4" /> System
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">Status</span>
                  <Badge variant={systemStatus === "healthy" ? "success" : "warning"}>
                    {systemStatus}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">Active Providers</span>
                  <span>{providersQuery.data?.filter((p) => p.is_enabled).length ?? "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">Providers with Traffic</span>
                  <span>{ov?.active_providers ?? "—"}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Top Providers</CardTitle></CardHeader>
              <CardContent>
                {(providers.data?.breakdown ?? []).length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">No provider data yet.</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Provider</TableHead>
                        <TableHead className="text-right">Requests</TableHead>
                        <TableHead className="text-right">Success</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(providers.data?.breakdown ?? []).slice(0, 5).map((p) => (
                        <TableRow key={p.provider}>
                          <TableCell>{p.provider}</TableCell>
                          <TableCell className="text-right">{p.total_requests}</TableCell>
                          <TableCell className="text-right">{p.success_rate}%</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">Recent Errors</CardTitle></CardHeader>
              <CardContent>
                {(errors.data?.errors ?? []).length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">No recent errors.</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
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
                          <TableCell className="max-w-xs truncate">{e.message}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="text-center">
            <Link href="/analytics" className="text-sm text-[var(--ring)] hover:underline">
              View full analytics →
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
