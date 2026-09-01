"use client";

import { DatabaseZap, ShieldCheck, Lock, AlertTriangle } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { SecurityMetricCard } from "@/components/security/security-metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const SAMPLE_LABEL = "Sample data — shown for UI review only.";

// Illustrative data-protection findings. NO sensitive values are shown — only
// the classification of data type and an occurrence count.
const FINDINGS = [
  { id: "DPL-01", dataType: "PII — email address", classification: "Personal Data", occurrence: 134, policy: "Mask", status: "open" as const },
  { id: "DPL-02", dataType: "Financial — card-like number", classification: "Sensitive", occurrence: 7, policy: "Block", status: "open" as const },
  { id: "DPL-03", dataType: "Credential — API key pattern", classification: "Secret", occurrence: 2, policy: "Block", status: "critical" as const },
  { id: "DPL-04", dataType: "Health-related term", classification: "Sensitive", occurrence: 11, policy: "Mask", status: "open" as const },
];

// Illustrative protections (sample only).
const PROTECTIONS = [
  { name: "Prompt redaction", engine: "Data Protection", enabled: true, description: "Redacts detected sensitive terms before they reach the model." },
  { name: "Output masking", engine: "Response Filter", enabled: true, description: "Masks sensitive values in model output before delivery." },
  { name: "Log sanitization", engine: "Logger", enabled: true, description: "Strips sensitive payloads from request/response logs." },
  { name: "Embedding isolation", engine: "Vector Guard", enabled: false, description: "Prevents embedding values from leaking into logs." },
];

export default function DataProtectionPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={DatabaseZap}
        title="Data Protection"
        description="Detect and control sensitive data flowing through your AI pipeline"
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 stagger-children">
        <SecurityMetricCard icon={Lock} label="Sensitive items detected" value={154} trend="down" trendValue="−18 this week" gradient="from-red-500 to-rose-400" />
        <SecurityMetricCard icon={ShieldCheck} label="Masked / blocked" value={149} gradient="from-emerald-500 to-green-400" />
        <SecurityMetricCard icon={DatabaseZap} label="Log entries sanitized" value="8.2k" gradient="from-blue-500 to-cyan-400" />
        <SecurityMetricCard icon={ShieldCheck} label="Protections active" value="3/4" gradient="from-violet-500 to-purple-400" />
      </div>

      {/* Sensitive data findings */}
      <Card className="overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <Lock className="h-4 w-4 text-[var(--primary)]" /> Sensitive data detected
          </CardTitle>
          <span className="text-[11px] text-[var(--muted-foreground)]">Values masked — never displayed raw</span>
        </CardHeader>
        <CardContent className="p-0">
          {FINDINGS.length === 0 ? (
            <EmptySecurityState
              icon={ShieldCheck}
              title="No sensitive data detected"
              description="When a sensitive data type is detected in traffic, its classification (never its raw value) will appear here."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Data type</TableHead>
                  <TableHead>Classification</TableHead>
                  <TableHead className="text-right">Occurrences</TableHead>
                  <TableHead>Policy</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {FINDINGS.map((f) => (
                  <TableRow key={f.id} className="group">
                    <TableCell>
                      <span className="font-medium">{f.dataType}</span>
                      <span className="block font-mono text-[11px] text-[var(--muted-foreground)]">{f.id}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={f.classification === "Secret" ? "destructive" : "warning"} className="text-[10px]">
                        {f.classification}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">{f.occurrence}</TableCell>
                    <TableCell><span className="text-xs">{f.policy}</span></TableCell>
                    <TableCell>
                      {f.status === "critical" ? <SeverityBadge severity="critical" /> : <Badge variant="warning" className="text-[10px]">Open</Badge>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Protections */}
      <Card className="overflow-hidden">
        <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
          <CardTitle className="text-sm font-semibold">Protections</CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-[var(--border)] p-0">
          {PROTECTIONS.map((p) => (
            <div key={p.name} className="flex items-start justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{p.name}</span>
                  <Badge variant="secondary" className="text-[10px]">{p.engine}</Badge>
                </div>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">{p.description}</p>
              </div>
              <Badge variant={p.enabled ? "success" : "warning"} className="shrink-0 text-[10px]">
                {p.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
