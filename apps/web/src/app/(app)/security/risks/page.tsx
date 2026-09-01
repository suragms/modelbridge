"use client";

import { AlertTriangle, ShieldAlert, BarChart3 } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
import { SecurityMetricCard } from "@/components/security/security-metric-card";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const SAMPLE_LABEL = "Sample data — shown for UI review only.";

interface RiskItem {
  id: string;
  title: string;
  category: string;
  likelihood: Severity;
  impact: Severity;
  level: Severity;
  status: StatusType;
  owner: string;
}

// Illustrative AI-specific risk register (sample only).
const RISKS: RiskItem[] = [
  { id: "RSK-51", title: "Prompt injection leading to data disclosure", category: "Security", likelihood: "high", impact: "high", level: "critical", status: "open", owner: "Sec Team" },
  { id: "RSK-50", title: "Model hallucination of sensitive procedure", category: "Reliability", likelihood: "medium", impact: "high", level: "high", status: "mitigated", owner: "Platform" },
  { id: "RSK-49", title: "Unsafe tool-use triggering unintended action", category: "Autonomy", likelihood: "medium", impact: "medium", level: "medium", status: "investigating", owner: "Model Gov" },
  { id: "RSK-48", title: "Training-data leakage in generated output", category: "Privacy", likelihood: "low", impact: "high", level: "medium", status: "open", owner: "Privacy" },
  { id: "RSK-47", title: "Bias amplification in production prompts", category: "Fairness", likelihood: "low", impact: "medium", level: "low", status: "closed", owner: "Ethics" },
];

const LEVELS = [
  { label: "Critical", count: 1, color: "bg-red-500" },
  { label: "High", count: 1, color: "bg-orange-500" },
  { label: "Medium", count: 2, color: "bg-amber-500" },
  { label: "Low", count: 1, color: "bg-blue-500" },
];

export default function AiRisksPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={ShieldAlert}
        title="AI Risks"
        description="Risk register for model, prompt, and autonomy-specific hazards"
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 stagger-children">
        <SecurityMetricCard icon={ShieldAlert} label="Total risks" value={RISKS.length} gradient="from-slate-500 to-gray-400" />
        <SecurityMetricCard icon={AlertTriangle} label="Open (active)" value={3} gradient="from-red-500 to-rose-400" />
        <SecurityMetricCard icon={BarChart3} label="Mitigated" value={1} gradient="from-emerald-500 to-green-400" />
        <SecurityMetricCard icon={BarChart3} label="Residual exposure" value="Med" gradient="from-amber-500 to-orange-400" />
      </div>

      {/* Heatmap */}
      <Card>
        <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
          <CardTitle className="text-sm font-semibold">Risk level distribution</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex gap-3 h-4 mb-6 overflow-hidden rounded-full">
            {LEVELS.map((l) => (
              <div
                key={l.label}
                className={l.color}
                style={{ flexGrow: l.count, flexBasis: "0%" }}
                title={`${l.label}: ${l.count}`}
                aria-label={`${l.label}: ${l.count}`}
              />
            ))}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {LEVELS.map((l) => (
              <div key={l.label} className="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 px-3 py-2">
                <span className={`h-2.5 w-2.5 rounded-full ${l.color}`} />
                <span className="text-xs">{l.label}</span>
                <span className="ml-auto text-xs font-bold">{l.count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {RISKS.length === 0 ? (
            <EmptySecurityState
              icon={ShieldAlert}
              title="No assessed risks"
              description="Assessments will appear here once a risk review is completed."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Risk</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Likelihood</TableHead>
                  <TableHead>Impact</TableHead>
                  <TableHead>Level</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {RISKS.map((r) => (
                  <TableRow key={r.id} className="group">
                    <TableCell>
                      <span className="font-medium">{r.title}</span>
                      <span className="block font-mono text-[11px] text-[var(--muted-foreground)]">{r.id} · {r.owner}</span>
                    </TableCell>
                    <TableCell><span className="text-xs">{r.category}</span></TableCell>
                    <TableCell><SeverityBadge severity={r.likelihood} showIcon={false} /></TableCell>
                    <TableCell><SeverityBadge severity={r.impact} showIcon={false} /></TableCell>
                    <TableCell><SeverityBadge severity={r.level} /></TableCell>
                    <TableCell><StatusBadge status={r.status} /></TableCell>
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
