"use client";

import { Activity } from "lucide-react";

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
import { useRequestLogs } from "@/lib/hooks";

export default function RequestsPage() {
  const logsQuery = useRequestLogs();
  const logs = logsQuery.data ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Requests</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Recent gateway traffic
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Request Logs</CardTitle>
        </CardHeader>
        <CardContent>
          {logsQuery.isLoading ? (
            <p className="py-8 text-center text-[var(--muted-foreground)]">Loading…</p>
          ) : logs.length === 0 ? (
            <div className="py-12 text-center">
              <Activity className="mx-auto h-8 w-8 text-[var(--muted-foreground)]" />
              <p className="mt-3 text-[var(--muted-foreground)]">
                No requests logged yet. Requests appear here once they are routed.
              </p>
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
                {logs.map((log, idx) => (
                  <TableRow key={log.id ?? idx}>
                    <TableCell>
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="font-medium">{log.model}</TableCell>
                    <TableCell>{log.provider}</TableCell>
                    <TableCell className="text-right">
                      {log.latency_ms.toFixed(0)}ms
                    </TableCell>
                    <TableCell>
                      <Badge variant={log.status === "success" ? "success" : "destructive"}>
                        {log.status}
                      </Badge>
                      {log.error && (
                        <p className="mt-1 max-w-xs truncate text-xs text-red-600" title={log.error}>
                          {log.error}
                        </p>
                      )}
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
