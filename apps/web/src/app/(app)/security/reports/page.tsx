"use client";

import { FileText, Download, AlertTriangle, Calendar } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const SAMPLE_LABEL = "Sample data — shown for UI review only.";

// Illustrative scheduled/emitted reports (sample only).
const REPORTS = [
  { id: "RPT-04", name: "Monthly Threat Summary", period: "August 2026", kind: "Scheduled", status: "Ready", generated: "Sep 1, 2026" },
  { id: "RPT-03", name: "Quarterly Posture Report", period: "Q3 2026", kind: "Scheduled", status: "Draft", generated: "—" },
  { id: "RPT-02", name: "Prompt Injection Deep-dive", period: "Jul 2026", kind: "On-demand", status: "Ready", generated: "Jul 28, 2026" },
  { id: "RPT-01", name: "Access Review", period: "Jun 2026", kind: "On-demand", status: "Ready", generated: "Jun 30, 2026" },
];

export default function SecurityReportsPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={FileText}
        title="Security Reports"
        description="Scheduled and on-demand reporting for stakeholders and audits"
        actions={
          <Button variant="outline" size="sm" className="hidden sm:inline-flex">
            <Calendar className="h-4 w-4" /> Schedule report
          </Button>
        }
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      <Card className="overflow-hidden">
        <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <FileText className="h-4 w-4 text-[var(--primary)]" /> Generated reports
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {REPORTS.length === 0 ? (
            <EmptySecurityState
              icon={FileText}
              title="No reports yet"
              description="Scheduled and on-demand reports will appear here with download options."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Report</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Kind</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {REPORTS.map((r) => (
                  <TableRow key={r.id} className="group">
                    <TableCell>
                      <span className="font-medium">{r.name}</span>
                      <span className="block font-mono text-[11px] text-[var(--muted-foreground)]">{r.id}</span>
                    </TableCell>
                    <TableCell className="text-xs">{r.period}</TableCell>
                    <TableCell><Badge variant="secondary" className="text-[10px]">{r.kind}</Badge></TableCell>
                    <TableCell><Badge variant={r.status === "Ready" ? "success" : "warning"} className="text-[10px]">{r.status}</Badge></TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" disabled={r.status !== "Ready"} aria-label={`Download ${r.name}`}>
                        <Download className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-8">
          <EmptySecurityState
            icon={FileText}
            title="Evidence-collection exports"
            description="Compliance evidence for a workspace can be bundled and exported here, respecting viewer permissions."
          />
        </CardContent>
      </Card>
    </div>
  );
}
