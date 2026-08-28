"use client";

import Link from "next/link";
import { useState } from "react";
import { Activity, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRequestLogs } from "@/lib/hooks";

function statusVariant(status: string) {
  if (status === "COMPLETED" || status === "success") return "success" as const;
  if (status === "FAILED" || status === "error") return "destructive" as const;
  return "secondary" as const;
}

export default function RequestsPage() {
  const [status, setStatus] = useState<string>("");
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [requestId, setRequestId] = useState("");
  const [page, setPage] = useState(0);
  const limit = 25;

  const logsQuery = useRequestLogs({
    limit,
    offset: page * limit,
    status: status || undefined,
    provider: provider || undefined,
    model: model || undefined,
    request_id: requestId || undefined,
  });

  const logs = logsQuery.data?.items ?? [];
  const total = logsQuery.data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Requests</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Explore gateway traffic with server-side filtering
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-[var(--muted-foreground)]" />
              <Input
                placeholder="Request ID"
                className="pl-8"
                value={requestId}
                onChange={(e) => { setRequestId(e.target.value); setPage(0); }}
              />
            </div>
            <Select
              value={status || "all"}
              onChange={(e) => { setStatus(e.target.value === "all" ? "" : e.target.value); setPage(0); }}
            >
              <option value="all">All statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
              <option value="PROCESSING">Processing</option>
            </Select>
            <Input
              placeholder="Provider"
              value={provider}
              onChange={(e) => { setProvider(e.target.value); setPage(0); }}
            />
            <Input
              placeholder="Model"
              value={model}
              onChange={(e) => { setModel(e.target.value); setPage(0); }}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Request Logs</CardTitle>
          <span className="text-sm text-[var(--muted-foreground)]">{total} total</span>
        </CardHeader>
        <CardContent>
          {logsQuery.isLoading ? (
            <p className="py-8 text-center text-[var(--muted-foreground)]">Loading…</p>
          ) : logs.length === 0 ? (
            <div className="py-12 text-center">
              <Activity className="mx-auto h-8 w-8 text-[var(--muted-foreground)]" />
              <p className="mt-3 text-[var(--muted-foreground)]">
                No requests match your filters.
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Request ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Requested</TableHead>
                    <TableHead>Selected</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead className="text-right">Latency</TableHead>
                    <TableHead className="text-right">Tokens</TableHead>
                    <TableHead className="text-right">Est. Cost</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id ?? log.request_id}>
                      <TableCell className="whitespace-nowrap text-xs">
                        {new Date(log.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/requests/${log.request_id}`}
                          className="font-mono text-xs text-[var(--ring)] hover:underline"
                        >
                          {log.request_id.slice(0, 16)}…
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(log.status)}>{log.status}</Badge>
                      </TableCell>
                      <TableCell className="text-[var(--muted-foreground)]">
                        {log.requested_model ?? log.model}
                      </TableCell>
                      <TableCell>{log.selected_model ?? log.model}</TableCell>
                      <TableCell>{log.provider}</TableCell>
                      <TableCell className="text-right">{log.latency_ms.toFixed(0)}ms</TableCell>
                      <TableCell className="text-right">
                        {log.total_tokens != null ? log.total_tokens : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        {log.estimated_total_cost != null
                          ? `$${log.estimated_total_cost.toFixed(4)}`
                          : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {totalPages > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-[var(--muted-foreground)]">
                    Page {page + 1} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages - 1}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
