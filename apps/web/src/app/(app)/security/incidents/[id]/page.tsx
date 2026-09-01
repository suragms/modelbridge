"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Flame,
  AlertTriangle,
  Link2,
  MessageSquare,
  ClipboardList,
} from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
import { ThreatTimeline, TimelineEvent } from "@/components/security/threat-timeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const SAMPLE_LABEL = "Sample incident — illustrative content for UI review only.";

const SUMMARY = {
  id: "INC-42",
  title: "Possible API-key misuse in production",
  severity: "critical" as Severity,
  status: "investigating" as StatusType,
  created: "3 hours ago",
  assignee: "Unassigned",
  description:
    "Multiple alerts from distinct sources correlate to a single suspicious pattern involving a production API key. Access appears to originate from an unusual scope. Investigation in progress; no sensitive values are displayed.",
};

const LINKED_ALERTS = [
  { id: "ALT-1024", title: "Suspicious prompt-injection pattern", severity: "high" as Severity },
  { id: "ALT-1021", title: "Unusual geographic origin", severity: "low" as Severity },
  { id: "ALT-1023", title: "Excessive token output from single request", severity: "medium" as Severity },
  { id: "ALT-1019", title: "New device for existing key", severity: "medium" as Severity },
];

const TIMELINE: TimelineEvent[] = [
  { id: "t1", timestamp: "3h ago", title: "First alert raised", description: "ALT-1024 flagged suspicious prompt pattern.", severity: "high", source: "Prompt Guard" },
  { id: "t2", timestamp: "2.5h ago", title: "Incident opened", description: "Alert correlation grouped 2 related signals.", severity: "medium", source: "Correlation Engine" },
  { id: "t3", timestamp: "1h ago", title: "Key scoped down", description: "Recommendation issued to rotate the affected credential.", severity: "info", source: "Responder" },
];

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <Link href="/security/incidents" className="inline-flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] hover:text-[var(--primary)] transition-colors">
          <ArrowLeft className="h-4 w-4" /> Back to Incidents
        </Link>
      </div>

      <SecurityHeader
        icon={Flame}
        title={SUMMARY.title}
        description={`INC-${id} · created ${SUMMARY.created}`}
        actions={
          <div className="flex items-center gap-2">
            <SeverityBadge severity={SUMMARY.severity} size="md" />
            <StatusBadge status={SUMMARY.status} size="md" />
          </div>
        }
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Left column */}
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <ClipboardList className="h-4 w-4 text-[var(--primary)]" /> Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <p className="text-sm leading-relaxed text-[var(--muted-foreground)]">{SUMMARY.description}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <Link2 className="h-4 w-4 text-[var(--primary)]" /> Linked Alerts ({LINKED_ALERTS.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="divide-y divide-[var(--border)] p-0">
              {LINKED_ALERTS.map((a) => (
                <div key={a.id} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <SeverityBadge severity={a.severity} />
                    <span className="truncate text-sm">{a.title}</span>
                  </div>
                  <span className="shrink-0 font-mono text-[11px] text-[var(--muted-foreground)]">{a.id}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <MessageSquare className="h-4 w-4 text-[var(--primary)]" /> Response Timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <ThreatTimeline events={TIMELINE} />
            </CardContent>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="text-sm font-semibold">Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 p-4">
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="flex-1">Escalate</Button>
                <Button variant="destructive" size="sm" className="flex-1">Resolve</Button>
              </div>
              <Button variant="outline" size="sm" className="w-full">Rotate affected key</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="text-sm font-semibold">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-4 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--muted-foreground)]">ID</span>
                <span className="font-mono text-xs">INC-{id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted-foreground)]">Created</span>
                <span className="text-xs">{SUMMARY.created}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted-foreground)]">Status</span>
                <StatusBadge status={SUMMARY.status} />
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted-foreground)]">Assignee</span>
                <Badge variant="secondary" className="text-[10px]">Unassigned</Badge>
              </div>
              <div>
                <p className="mb-1.5 text-[var(--muted-foreground)]">Communications</p>
                <div className="flex gap-2">
                  <Input placeholder="Post status update..." className="h-8 text-xs" />
                  <Button size="sm" variant="secondary">Post</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
