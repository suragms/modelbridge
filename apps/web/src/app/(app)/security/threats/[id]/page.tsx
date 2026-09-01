"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Crosshair,
  AlertTriangle,
  ShieldBan,
  Flag,
  MapPin,
  FileText,
} from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
import { ThreatTimeline, TimelineEvent } from "@/components/security/threat-timeline";
import { EvidencePanel } from "@/components/security/evidence-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// Sample detail context (see list page note)
const SAMPLE_LABEL =
  "Sample detail — illustrative content for UI review only. Live threat telemetry is not connected.";

interface ThreatDetail {
  name: string;
  id: string;
  tactic: string;
  technique: string;
  severity: Severity;
  status: StatusType;
  source: string;
  detected: string;
  description: string;
  mitre: string;
}

const SAMPLE_DETAIL: Record<string, ThreatDetail> = {
  "221": {
    name: "Prompt injection — direct",
    id: "THR-221",
    tactic: "Initial Access",
    technique: "Phishing → Phishing for Information",
    severity: "critical",
    status: "open",
    source: "Prompt Guard",
    detected: "12 minutes ago",
    description:
      "A user-controlled message contained an explicit instruction to override system directives. The prompt attempted to make the model ignore its safety constraints and disclose protected values.",
    mitre: "T1566",
  },
};

function getDetail(id: string): ThreatDetail {
  return SAMPLE_DETAIL[id] ?? {
    name: `Detected threat ${id}`,
    id: `THR-${id}`,
    tactic: "Unclassified",
    technique: "—",
    severity: "medium" as Severity,
    status: "open" as StatusType,
    source: "Detection source",
    detected: "recently",
    description:
      "Detailed telemetry for this threat is not available in the sample set. Connect a detection source to view full analysis.",
    mitre: "T0000",
  };
}

const EVENTS: TimelineEvent[] = [
  { id: "e1", timestamp: "12 minutes ago", title: "Threat detected", description: "Pattern matched by Prompt Guard sensor.", severity: "high", source: "Prompt Guard" },
  { id: "e2", timestamp: "11 minutes ago", title: "Alert raised", description: "High-severity alert ALT-1024 created from this threat.", severity: "medium", source: "Alert Engine" },
  { id: "e3", timestamp: "8 minutes ago", title: "Blocked request", description: "Suspected request quarantined; no response returned to caller.", severity: "info", source: "Gateway" },
];

export default function ThreatDetailPage() {
  const { id } = useParams<{ id: string }>();
  const threat = getDetail(id);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <Link href="/security/threats" className="inline-flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] hover:text-[var(--primary)] transition-colors">
          <ArrowLeft className="h-4 w-4" /> Back to Threats
        </Link>
      </div>

      <SecurityHeader
        icon={Crosshair}
        title={threat.name}
        description={`${threat.id} · detected ${threat.detected}`}
        actions={
          <div className="flex items-center gap-2">
            <SeverityBadge severity={threat.severity} size="md" />
            <StatusBadge status={threat.status} size="md" />
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
                <ShieldBan className="h-4 w-4 text-[var(--primary)]" /> Analysis
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <p className="text-sm leading-relaxed text-[var(--muted-foreground)]">{threat.description}</p>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 p-3">
                  <p className="text-[11px] text-[var(--muted-foreground)]">Tactic</p>
                  <p className="mt-1 text-xs font-semibold">{threat.tactic}</p>
                </div>
                <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 p-3">
                  <p className="text-[11px] text-[var(--muted-foreground)]">Technique</p>
                  <p className="mt-1 text-xs font-semibold">{threat.technique}</p>
                </div>
                <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 p-3">
                  <p className="text-[11px] text-[var(--muted-foreground)]">MITRE</p>
                  <p className="mt-1 font-mono text-xs font-semibold">{threat.mitre}</p>
                </div>
                <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 p-3">
                  <p className="text-[11px] text-[var(--muted-foreground)]">Source</p>
                  <p className="mt-1 text-xs font-semibold">{threat.source}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <MapPin className="h-4 w-4 text-[var(--primary)]" /> Timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <ThreatTimeline events={EVENTS} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <FileText className="h-4 w-4 text-[var(--primary)]" /> Evidence
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <EvidencePanel
                items={[
                  { id: "ev-1", title: "Prompt payload", type: "Request", timestamp: "12m ago", description: "Bytes of the flagged instruction.", sensitive: true },
                  { id: "ev-2", title: "Model response (blocked)", type: "Response", timestamp: "12m ago", description: "No response returned — request quarantined." },
                  { id: "ev-3", title: "Source context", type: "Metadata", timestamp: "12m ago", description: "Caller identity and project scoping for review." },
                ]}
              />
            </CardContent>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <Flag className="h-4 w-4 text-[var(--primary)]" /> Response Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-4">
              <Button variant="destructive" size="sm" className="w-full">Block threat pattern</Button>
              <Button variant="outline" size="sm" className="w-full">Escalate to incident</Button>
              <Button variant="ghost" size="sm" className="w-full">Mark as false positive</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
              <CardTitle className="text-sm font-semibold">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-4 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--muted-foreground)]">ID</span>
                <span className="font-mono text-xs">{threat.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted-foreground)]">Detected</span>
                <span className="text-xs">{threat.detected}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted-foreground)]">Status</span>
                <StatusBadge status={threat.status} />
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted-foreground)]">Assignee</span>
                <Badge variant="secondary" className="text-[10px]">Unassigned</Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
