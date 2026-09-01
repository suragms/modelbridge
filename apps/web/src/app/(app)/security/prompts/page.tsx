"use client";

import { MessageSquareWarning, ShieldCheck, AlertTriangle } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { SecurityMetricCard } from "@/components/security/security-metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const SAMPLE_LABEL = "Sample data — shown for UI review only.";

// Illustrative prompt-classification findings (sample only).
const PROMPT_FINDINGS = [
  { id: "PSC-01", category: "Direct prompt injection", count: 12, trend: "up" as const, severity: "critical" as Severity },
  { id: "PSC-02", category: "Indirect prompt injection", count: 4, trend: "down" as const, severity: "high" as Severity },
  { id: "PSC-03", category: "Jailbreak / role-play bypass", count: 7, trend: "up" as const, severity: "high" as Severity },
  { id: "PSC-04", category: "Sensitive-information elicitation", count: 3, trend: "down" as const, severity: "medium" as Severity },
  { id: "PSC-05", category: "Token-smuggling payload", count: 2, trend: "flat" as const, severity: "medium" as Severity },
];

// Illustrative defensive controls (sample only).
const GUARDRAILS = [
  { name: "System-prompt anchoring", engine: "Prompt Guard", enabled: true, description: "Verifies model behavior stays within declared system boundaries." },
  { name: "Context isolation", engine: "Guardrails", enabled: true, description: "Separates system, tool, and user context layers." },
  { name: "Output constraint schema", engine: "Guardrails", enabled: true, description: "Enforces structured output to block injection of control directives." },
  { name: "Sensitive-term blocking", engine: "Data Protection", enabled: false, description: "Blocks known sensitive tokens from being elicited." },
];

export default function PromptSecurityPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={MessageSquareWarning}
        title="Prompt Security"
        description="Detection and mitigation of adversarial prompt techniques"
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 stagger-children">
        <SecurityMetricCard icon={MessageSquareWarning} label="Prompts scanned" value="12.4k" gradient="from-violet-500 to-purple-400" />
        <SecurityMetricCard icon={AlertTriangle} label="Suspicious" value={28} trend="up" trendValue="+4 this week" gradient="from-red-500 to-rose-400" />
        <SecurityMetricCard icon={ShieldCheck} label="Blocked" value={22} gradient="from-emerald-500 to-green-400" />
        <SecurityMetricCard icon={ShieldCheck} label="Guardrails active" value="3/4" gradient="from-blue-500 to-cyan-400" />
      </div>

      {/* Detection methods */}
      <Card>
        <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="h-4 w-4 text-[var(--primary)]" /> How detection works
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-sm text-[var(--muted-foreground)]">
          <p>
            Prompts are classified by dedicated sensors that look for known adversarial patterns — no raw prompt
            content is stored. Findings are grouped by technique and labelled with severity. Detection methods can
            be configured per guardrail below.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Classified findings */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="text-sm font-semibold">Techniques detected (28 days)</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-[var(--border)] p-0">
            {PROMPT_FINDINGS.map((f) => (
              <div key={f.id} className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-2 min-w-0">
                  <SeverityBadge severity={f.severity} />
                  <span className="truncate text-sm">{f.category}</span>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <Badge variant="outline" className="font-mono">{f.count}</Badge>
                  <span className={`text-[11px] ${f.trend === "up" ? "text-red-500" : f.trend === "down" ? "text-emerald-500" : "text-[var(--muted-foreground)]"}`}>
                    {f.trend === "up" ? "▲" : f.trend === "down" ? "▼" : "—"} {f.trend}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Guardrails */}
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="text-sm font-semibold">Guardrails</CardTitle>
            <Button variant="outline" size="sm">Manage</Button>
          </CardHeader>
          <CardContent className="divide-y divide-[var(--border)] p-0">
            {GUARDRAILS.map((g) => (
              <div key={g.name} className="flex items-start justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{g.name}</span>
                    <Badge variant="secondary" className="text-[10px]">{g.engine}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted-foreground)]">{g.description}</p>
                </div>
                <Badge variant={g.enabled ? "success" : "warning"} className="shrink-0 text-[10px]">
                  {g.enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
