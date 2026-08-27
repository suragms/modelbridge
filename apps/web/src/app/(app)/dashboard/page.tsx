"use client";

import Link from "next/link";
import { Activity, Boxes, Server, ShieldCheck } from "lucide-react";

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
  useHealth,
  useModels,
  useProviders,
  useRequestLogs,
} from "@/lib/hooks";

export default function DashboardPage() {
  const providersQuery = useProviders();
  const modelsQuery = useModels();
  const requestsQuery = useRequestLogs();
  const healthQuery = useHealth();

  const activeProviders =
    providersQuery.data?.filter((p) => p.is_enabled).length ?? null;
  const availableModels = modelsQuery.data ? modelsQuery.data.length : null;
  const totalRequests = requestsQuery.data ? requestsQuery.data.length : null;

  const systemStatus: string | null = healthQuery.data
    ? healthQuery.data.status === "healthy"
      ? "Healthy"
      : "Degraded"
    : null;

  const loading =
    providersQuery.isLoading || modelsQuery.isLoading || requestsQuery.isLoading;

  const recentRequests = requestsQuery.data?.slice(0, 10) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Overview of your gateway
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">
              Active Providers
            </CardTitle>
            <Server className="h-4 w-4 text-[var(--muted-foreground)]" />
          </CardHeader>
          <CardContent>
            {loading || activeProviders === null ? (
              <p className="text-[var(--muted-foreground)]">—</p>
            ) : activeProviders === 0 ? (
              <div>
                <p className="text-xl font-bold">0</p>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                  Add a provider to get started.
                </p>
              </div>
            ) : (
              <p className="text-2xl font-bold">{activeProviders}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">
              Available Models
            </CardTitle>
            <Boxes className="h-4 w-4 text-[var(--muted-foreground)]" />
          </CardHeader>
          <CardContent>
            {loading || availableModels === null ? (
              <p className="text-[var(--muted-foreground)]">—</p>
            ) : availableModels === 0 ? (
              <div>
                <p className="text-xl font-bold">0</p>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                  Discover models from a provider.
                </p>
              </div>
            ) : (
              <p className="text-2xl font-bold">{availableModels}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">
              Total Requests
            </CardTitle>
            <Activity className="h-4 w-4 text-[var(--muted-foreground)]" />
          </CardHeader>
          <CardContent>
            {loading || totalRequests === null ? (
              <p className="text-[var(--muted-foreground)]">—</p>
            ) : (
              <p className="text-2xl font-bold">{totalRequests}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium text-[var(--muted-foreground)]">
              System Status
            </CardTitle>
            <ShieldCheck className="h-4 w-4 text-[var(--muted-foreground)]" />
          </CardHeader>
          <CardContent>
            {systemStatus ? (
              <Badge variant={systemStatus === "Healthy" ? "success" : "warning"}>
                {systemStatus}
              </Badge>
            ) : (
              <p className="text-[var(--muted-foreground)]">Unknown</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Requests</CardTitle>
        </CardHeader>
        <CardContent>
          {requestsQuery.isLoading ? (
            <p className="py-8 text-center text-[var(--muted-foreground)]">Loading…</p>
          ) : recentRequests.length === 0 ? (
            <div className="py-10 text-center">
              <p className="text-[var(--muted-foreground)]">
                No requests yet. Route your first request through{" "}
                <code className="rounded bg-[var(--muted)] px-1">/v1/chat/completions</code>.
              </p>
              <Link
                href="/providers"
                className="mt-4 inline-block text-sm text-[var(--ring)] hover:underline"
              >
                Add a provider →
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead className="text-right">Latency</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentRequests.map((log, idx) => (
                  <TableRow key={log.id ?? idx}>
                    <TableCell>
                      {new Date(log.created_at).toLocaleTimeString()}
                    </TableCell>
                    <TableCell>{log.model}</TableCell>
                    <TableCell>{log.provider}</TableCell>
                    <TableCell className="text-right">
                      {log.latency_ms.toFixed(0)}ms
                    </TableCell>
                    <TableCell>
                      <Badge variant={log.status === "success" ? "success" : "destructive"}>
                        {log.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
