"use client";

import Link from "next/link";
import { Crosshair, Filter, Search, ArrowUpDown } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// Sample data — clearly labelled, never to be mistaken for real detections.
const SAMPLE_LABEL =
  "Sample data — shown for UI review only. Connect a threat feed to see real findings.";

interface ThreatRow {
  id: string;
  name: string;
  tactic: string;
  technique: string;
  severity: Severity;
  status: StatusType;
  source: string;
  detected: string;
}

const THREATS: ThreatRow[] = [
  { id: "THR-221", name: "Prompt injection — direct", tactic: "Initial Access", technique: "T1566", severity: "critical", status: "open", source: "Prompt Guard", detected: "12m ago" },
  { id: "THR-220", name: "Jailbreak — role-play bypass", tactic: "Execution", technique: "T1566.001", severity: "high", status: "investigating", source: "Guardrails", detected: "38m ago" },
  { id: "THR-219", name: "Sensitive data extraction attempt", tactic: "Exfiltration", technique: "T1567", severity: "high", status: "open", source: "Data Protection", detected: "1h ago" },
  { id: "THR-218", name: "Token-smuggling payload", tactic: "Initial Access", technique: "T1566", severity: "medium", status: "open", source: "Prompt Guard", detected: "2h ago" },
  { id: "THR-217", name: "Malicious tool-use pattern", tactic: "Execution", technique: "T1059", severity: "medium", status: "mitigated", source: "Anomaly Detector", detected: "5h ago" },
  { id: "THR-216", name: "Prompt injection — indirect", tactic: "Initial Access", technique: "T1566.002", severity: "high", status: "resolved", source: "Prompt Guard", detected: "1d ago" },
  { id: "THR-215", name: "Embedding leak into log", tactic: "Exfiltration", technique: "T1567.003", severity: "low", status: "closed", source: "Data Protection", detected: "2d ago" },
];

export default function ThreatsPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={Crosshair}
        title="Threats"
        description="Detected adversarial patterns against your AI gateway and models"
      />

      {SAMPLE_LABEL && (
        <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
          <Filter className="h-4 w-4 text-[var(--severity-medium)]" />
          {SAMPLE_LABEL}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
              <Input placeholder="Search threats by name, tactic, or ID..." className="pl-9" />
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="gap-1.5 cursor-pointer hover:bg-[var(--muted)]">
                <Filter className="h-3 w-3" /> Filter
              </Badge>
              <Badge variant="outline" className="gap-1.5 cursor-pointer hover:bg-[var(--muted)]">
                <ArrowUpDown className="h-3 w-3" /> Sort
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Threats table */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {THREATS.length === 0 ? (
            <EmptySecurityState
              icon={Crosshair}
              title="No threats detected"
              description="When a detection source flags an adversarial pattern, it will appear here with full MITRE ATT&CK mapping and response actions."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Threat</TableHead>
                  <TableHead>Tactic / Technique</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead className="text-right">Detected</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {THREATS.map((t) => (
                  <TableRow key={t.id} className="group">
                    <TableCell>
                      <Link href={`/security/threats/${t.id.replace("THR-", "")}`} className="block">
                        <span className="font-medium text-[var(--primary)] group-hover:underline">{t.name}</span>
                        <span className="block font-mono text-[11px] text-[var(--muted-foreground)]">{t.id}</span>
                      </Link>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs">{t.tactic}</span>
                      <span className="block font-mono text-[11px] text-[var(--muted-foreground)]">{t.technique}</span>
                    </TableCell>
                    <TableCell><SeverityBadge severity={t.severity} /></TableCell>
                    <TableCell><StatusBadge status={t.status} /></TableCell>
                    <TableCell className="text-xs text-[var(--muted-foreground)]">{t.source}</TableCell>
                    <TableCell className="text-right text-xs text-[var(--muted-foreground)]">{t.detected}</TableCell>
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
