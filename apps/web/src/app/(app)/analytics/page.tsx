"use client";

import { useMemo, useState } from "react";
import { BarChart3, DollarSign, Timer, Zap } from "lucide-react";

import { TimeSeriesChart } from "@/components/charts/time-series-chart";
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
  useAnalyticsLatency,
  useAnalyticsModels,
  useAnalyticsOverview,
  useAnalyticsProviders,
  useAnalyticsRequests,
  useAnalyticsTokens,
} from "@/lib/hooks";

type DateRange = "24h" | "7d" | "30d" | "all";

function rangeToDates(range: DateRange): { start?: string; end?: string } {
  if (range === "all") return {};
  const end = new Date();
  const start = new Date();
  if (range === "24h") start.setHours(start.getHours() - 24);
  else if (range === "7d") start.setDate(start.getDate() - 7);
  else start.setDate(start.getDate() - 30);
  return { start: start.toISOString(), end: end.toISOString() };
}

export default function AnalyticsPage() {
  const [range, setRange] = useState<DateRange>("7d");
  const dates = useMemo(() => rangeToDates(range), [range]);

  const overview = useAnalyticsOverview(dates);
  const requests = useAnalyticsRequests(dates);
  const tokens = useAnalyticsTokens(dates);
  const cost = useAnalyticsCost(dates);
  const latency = useAnalyticsLatency(dates);
  const providers = useAnalyticsProviders(dates);
  const models = useAnalyticsModels(dates);
  const errors = useAnalyticsErrors(dates);

  const ov = overview.data;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Real usage metrics from your gateway traffic
          </p>
        </div>
        <div className="flex gap-2">
          {(["24h", "7d", "30d", "all"] as DateRange[]).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                range === r
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                  : "bg-[var(--muted)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              {r === "24h" ? "Last 24 Hours" : r === "7d" ? "Last 7 Days" : r === "30d" ? "Last 30 Days" : "All Time"}
            </button>
          ))}
        </div>
      </div>

      {!ov?.has_data && !overview.isLoading ? (
        <Card>
          <CardContent className="py-12 text-center text-[var(--muted-foreground)]">
            No request data available yet. Route traffic through the gateway to see analytics.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard icon={BarChart3} label="Requests" value={ov?.total_requests} loading={overview.isLoading} />
            <MetricCard icon={Zap} label="Total Tokens" value={ov?.total_tokens} loading={overview.isLoading} />
            <MetricCard
              icon={DollarSign}
              label="Est. Cost"
              value={ov?.estimated_total_cost != null ? `$${ov.estimated_total_cost.toFixed(4)}` : undefined}
              loading={overview.isLoading}
              subtitle="Estimated — not exact billing"
            />
            <MetricCard
              icon={Timer}
              label="Avg Latency"
              value={ov?.average_latency_ms != null ? `${ov.average_latency_ms.toFixed(0)} ms` : undefined}
              loading={overview.isLoading}
            />
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
              <CardHeader>
                <CardTitle className="text-base">Estimated Cost Over Time</CardTitle>
              </CardHeader>
              <CardContent>
                <TimeSeriesChart
                  data={cost.data?.data ?? []}
                  label="Cost (USD, estimated)"
                  valueFormatter={(v) => `$${v.toFixed(4)}`}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Latency Over Time</CardTitle></CardHeader>
              <CardContent>
                <TimeSeriesChart
                  data={latency.data?.data ?? []}
                  label="Latency (ms)"
                  valueFormatter={(v) => `${v.toFixed(0)} ms`}
                />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Provider Breakdown</CardTitle></CardHeader>
              <CardContent>
                <ProviderTable data={providers.data?.breakdown ?? []} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Model Breakdown</CardTitle></CardHeader>
              <CardContent>
                <ModelTable data={models.data ?? []} />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle className="text-base">Recent Errors</CardTitle></CardHeader>
            <CardContent>
              {(errors.data?.errors ?? []).length === 0 ? (
                <p className="py-4 text-center text-sm text-[var(--muted-foreground)]">No errors in this period.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Provider</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead>Message</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(errors.data?.errors ?? []).map((e) => (
                      <TableRow key={e.request_id}>
                        <TableCell className="text-xs">{new Date(e.timestamp).toLocaleString()}</TableCell>
                        <TableCell>{e.error_type}</TableCell>
                        <TableCell>{e.provider}</TableCell>
                        <TableCell>{e.model}</TableCell>
                        <TableCell className="max-w-xs truncate">{e.message}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  loading,
  subtitle,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value?: string | number;
  loading?: boolean;
  subtitle?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">{label}</CardTitle>
        <Icon className="h-4 w-4 text-[var(--muted-foreground)]" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-[var(--muted-foreground)]">—</p>
        ) : (
          <>
            <p className="text-2xl font-bold">{value ?? 0}</p>
            {subtitle && <p className="mt-1 text-xs text-[var(--muted-foreground)]">{subtitle}</p>}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ProviderTable({ data }: { data: Array<Record<string, unknown>> }) {
  if (!data.length) return <p className="text-sm text-[var(--muted-foreground)]">No provider data.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Provider</TableHead>
          <TableHead className="text-right">Requests</TableHead>
          <TableHead className="text-right">Success</TableHead>
          <TableHead className="text-right">Est. Cost</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((p) => (
          <TableRow key={String(p.provider)}>
            <TableCell>{String(p.provider)}</TableCell>
            <TableCell className="text-right">{String(p.total_requests)}</TableCell>
            <TableCell className="text-right">{String(p.success_rate)}%</TableCell>
            <TableCell className="text-right">${Number(p.estimated_cost).toFixed(4)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ModelTable({ data }: { data: Array<Record<string, unknown>> }) {
  if (!data.length) return <p className="text-sm text-[var(--muted-foreground)]">No model data.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Model</TableHead>
          <TableHead>Provider</TableHead>
          <TableHead className="text-right">Requests</TableHead>
          <TableHead className="text-right">Tokens</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((m) => (
          <TableRow key={`${m.model}-${m.provider}`}>
            <TableCell>{String(m.model)}</TableCell>
            <TableCell>{String(m.provider)}</TableCell>
            <TableCell className="text-right">{String(m.total_requests)}</TableCell>
            <TableCell className="text-right">{String(m.total_tokens)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
