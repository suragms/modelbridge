"use client";

import Link from "next/link";
import { Flame, AlertTriangle, Plus } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const SAMPLE_LABEL = "Sample data — shown for UI review only.";

interface IncidentRow {
  id: string;
  numericId: string;
  title: string;
  severity: Severity;
  status: StatusType;
  assignee: string;
  updated: string;
  alertsLinked: number;
  duration: string;
}

const INCIDENTS: IncidentRow[] = [
  { id: "INC-42", numericId: "42", title: "Possible API-key misuse in production", severity: "critical", status: "investigating", assignee: "Unassigned", updated: "3h ago", alertsLinked: 4, duration: "3h" },
  { id: "INC-41", numericId: "41", title: "Prompt injection on public playground", severity: "high", status: "open", assignee: "Sec Team", updated: "1d ago", alertsLinked: 2, duration: "1d" },
  { id: "INC-40", numericId: "40", title: "Spike in error-rate after model swap", severity: "medium", status: "resolved", assignee: "Platform", updated: "2d ago", alertsLinked: 1, duration: "1d" },
];

export default function IncidentsPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={Flame}
        title="Incidents"
        description="Correlated security events requiring coordinated response"
        actions={
          <Button variant="gradient" size="sm" className="hidden sm:inline-flex">
            <Plus className="h-4 w-4" /> New incident
          </Button>
        }
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      {INCIDENTS.length === 0 ? (
        <EmptySecurityState
          icon={Flame}
          title="No incidents"
          description="When correlated alerts are grouped into an incident, it will appear here with full response tracking."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 stagger-children">
          {INCIDENTS.map((inc) => (
            <Link key={inc.id} href={`/security/incidents/${inc.numericId}`} className="card-interactive group p-5">
              <div className="flex items-start justify-between">
                <SeverityBadge severity={inc.severity} />
                <span className="font-mono text-[11px] text-[var(--muted-foreground)]">{inc.id}</span>
              </div>
              <h3 className="mt-3 text-sm font-semibold group-hover:text-[var(--primary)] transition-colors">
                {inc.title}
              </h3>
              <div className="mt-3 flex items-center justify-between">
                <StatusBadge status={inc.status} />
                <span className="text-[11px] text-[var(--muted-foreground)]">updated {inc.updated}</span>
              </div>
              <div className="mt-4 flex items-center gap-2 border-t border-[var(--border)] pt-3 text-[11px] text-[var(--muted-foreground)]">
                <Badge variant="secondary" className="text-[10px]">{inc.alertsLinked} alerts</Badge>
                <span>·</span>
                <span>{inc.assignee}</span>
                <span className="ml-auto">{inc.duration}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
