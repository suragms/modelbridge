"use client";

import Link from "next/link";
import {
  ShieldAlert,
  Crosshair,
  BellRing,
  Flame,
  AlertTriangle,
  ArrowRight,
  FileCheck,
  Lock,
} from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SecurityMetricCard } from "@/components/security/security-metric-card";
import { SecurityPostureCard } from "@/components/security/security-posture-card";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
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

// ── Sample context ─────────────────────────────────────────────
// These are illustrative mock entries rendered for a complete UI review.
// They are clearly labelled as sample data below so they are never
// mistaken for real detections. No live data is fetched yet.
const SAMPLE = true;
const SAMPLE_LABEL =
  "Sample data — shown for UI review only. Connect a detection source to see real findings.";

const RECENT_ALERTS = [
  { id: "ALT-1024", title: "Suspicious prompt-injection pattern", severity: "high" as Severity, status: "open" as StatusType, source: "Prompt Guard", time: "2m ago" },
  { id: "ALT-1023", title: "Excessive token output from single request", severity: "medium" as Severity, status: "investigating" as StatusType, source: "Anomaly Detector", time: "18m ago" },
  { id: "ALT-1022", title: "Embedding leak into logs", severity: "high" as Severity, status: "open" as StatusType, source: "Data Protection", time: "41m ago" },
  { id: "ALT-1021", title: "Unusual geographic origin", severity: "low" as Severity, status: "closed" as StatusType, source: "Access Control", time: "1h ago" },
  { id: "ALT-1020", title: "Rate limit threshold crossed", severity: "info" as Severity, status: "resolved" as StatusType, source: "Guardrails", time: "2h ago" },
];

const OPEN_INCIDENTS = [
  { id: "INC-42", title: "Possible API-key misuse in production", severity: "critical" as Severity, status: "investigating" as StatusType, updated: "3h ago" },
  { id: "INC-41", title: "Prompt injection on public playground", severity: "high" as Severity, status: "open" as StatusType, updated: "1d ago" },
  { id: "INC-40", title: "Spike in error-rate after model swap", severity: "medium" as Severity, status: "resolved" as StatusType, updated: "2d ago" },
];

export default function SecurityOverviewPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={ShieldAlert}
        title="Security Overview"
        description="AI Security Operations Center — posture, threats, and response in one place"
        actions={
          <Link
            href="/security/threats"
            className="hidden sm:inline-flex h-9 items-center gap-2 rounded-lg px-4 text-sm font-medium text-white shadow-sm transition-all hover:shadow-md hover:opacity-90 bg-[var(--brand-gradient)] active:scale-[0.98]"
          >
            Investigate threats <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />

      {SAMPLE && (
        <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
          <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
          {SAMPLE_LABEL}
        </div>
      )}

      {/* Metric cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 stagger-children">
        <SecurityMetricCard icon={Crosshair} label="Open Threats" value={42} gradient="from-red-500 to-rose-400" />
        <SecurityMetricCard icon={BellRing} label="Active Alerts" value={17} trend="up" trendValue="+6 this week" gradient="from-amber-500 to-orange-400" />
        <SecurityMetricCard icon={Flame} label="Open Incidents" value={3} gradient="from-rose-500 to-pink-400" />
        <SecurityMetricCard icon={FileCheck} label="Policies Enforced" value={12} trend="flat" trendValue="of 14" gradient="from-emerald-500 to-green-400" />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Posture */}
        <Card className="lg:col-span-1">
          <CardContent className="p-0">
            <SecurityPostureCard
              overallScore={74}
              categories={[
                { label: "Data Protection", score: 82 },
                { label: "Prompt Security", score: 78 },
                { label: "Access Control", score: 71 },
                { label: "Model Governance", score: 65 },
              ]}
            />
          </CardContent>
        </Card>

        {/* Recent alerts */}
        <Card className="lg:col-span-2 overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <BellRing className="h-4 w-4 text-[var(--primary)]" /> Recent Alerts
            </CardTitle>
            <Link href="/security/alerts" className="text-xs text-[var(--primary)] hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Alert</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead className="text-right">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {RECENT_ALERTS.slice(0, 5).map((a) => (
                  <TableRow key={a.id} className="group">
                    <TableCell className="max-w-[280px]">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={a.severity} />
                        <span className="truncate font-medium">{a.title}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-[var(--muted-foreground)]">{a.source}</TableCell>
                    <TableCell className="text-right">
                      <StatusBadge status={a.status} />
                      <span className="ml-2 hidden sm:inline text-[11px] text-[var(--muted-foreground)]">{a.time}</span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* Open incidents + posture breakdown */}
      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <Flame className="h-4 w-4 text-[var(--severity-critical)]" /> Open Incidents
            </CardTitle>
            <Link href="/security/incidents" className="text-xs text-[var(--primary)] hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="divide-y divide-[var(--border)] p-0">
            {OPEN_INCIDENTS.map((inc) => (
              <Link
                key={inc.id}
                href={`/security/incidents/${inc.id.toLowerCase().replace("inc-", "")}`}
                className="flex items-center justify-between gap-3 px-4 py-3 transition-colors hover:bg-[var(--muted)]/40"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={inc.severity} />
                    <span className="truncate text-sm font-medium">{inc.title}</span>
                  </div>
                  <p className="mt-1 text-[11px] font-mono text-[var(--muted-foreground)]">
                    {inc.id} · updated {inc.updated}
                  </p>
                </div>
                <StatusBadge status={inc.status} />
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <Lock className="h-4 w-4 text-[var(--primary)]" /> Detection Coverage
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Prompt injection", state: "Active" as const, pct: 96 },
                { label: "Data exfiltration", state: "Active" as const, pct: 88 },
                { label: "Anomalous traffic", state: "Active" as const, pct: 79 },
                { label: "Jailbreak attempts", state: "Draft" as const, pct: 41 },
              ].map((d) => (
                <div key={d.label} className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium">{d.label}</span>
                    <Badge variant={d.state === "Active" ? "success" : "warning"} className="text-[10px]">
                      {d.state}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xl font-bold">{d.pct}%</p>
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                    <div
                      className="h-full rounded-full bg-[var(--brand-gradient)]"
                      style={{ width: `${d.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-[11px] text-[var(--muted-foreground)]">
              Coverage indicates the share of traffic evaluated by each detector. Configure sources in
              Detection &amp; Response.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
