"use client";

import { useState } from "react";
import { BellRing, AlertTriangle, Filter, Search } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { AlertCard } from "@/components/security/alert-card";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogBody, DialogFooter } from "@/components/ui/dialog";

const SAMPLE_LABEL = "Sample data — shown for UI review only.";

interface AlertRow {
  id: string;
  title: string;
  severity: Severity;
  status: StatusType;
  source: string;
  time: string;
  description: string;
  response: string[];
}

const ALERTS: AlertRow[] = [
  { id: "ALT-1024", title: "Suspicious prompt-injection pattern", severity: "high", status: "open", source: "Prompt Guard", time: "2m ago", description: "A message contained directives that attempt to override system instructions.", response: ["Block pattern", "Escalate to incident"] },
  { id: "ALT-1023", title: "Excessive token output from single request", severity: "medium", status: "investigating", source: "Anomaly Detector", time: "18m ago", description: "One request produced output far outside the expected token distribution.", response: ["Review call", "Set limit"] },
  { id: "ALT-1022", title: "Embedding leak into logs", severity: "high", status: "open", source: "Data Protection", time: "41m ago", description: "Model output containing embedding values was written to application logs.", response: ["Redact", "Block source"] },
  { id: "ALT-1021", title: "Unusual geographic origin", severity: "low", status: "closed", source: "Access Control", time: "1h ago", description: "A request originated from an unexpected region for this API key.", response: ["Acknowledge"] },
  { id: "ALT-1020", title: "Rate limit threshold crossed", severity: "info", status: "resolved", source: "Guardrails", time: "2h ago", description: "Transient burst briefly exceeded the configured rate limit.", response: [] },
];

export default function AlertsPage() {
  const [selected, setSelected] = useState<AlertRow | null>(null);
  const [open, setOpen] = useState(false);

  const openAlert = (a: AlertRow) => {
    setSelected(a);
    setOpen(true);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={BellRing}
        title="Alerts"
        description="Signals from detection sources, awaiting review and triage"
        actions={
          <Button variant="outline" size="sm" className="hidden sm:inline-flex">
            <Filter className="h-4 w-4" /> Filter
          </Button>
        }
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
        <Input placeholder="Search alerts..." className="pl-9" />
      </div>

      {ALERTS.length === 0 ? (
        <EmptySecurityState
          icon={BellRing}
          title="No alerts"
          description="When a detection source raises a signal, it will appear here for review and triage."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {ALERTS.map((a) => (
            <AlertCard
              key={a.id}
              id={a.id}
              title={a.title}
              description={a.description}
              severity={a.severity}
              status={a.status}
              source={a.source}
              timestamp={a.time}
              onClick={() => openAlert(a)}
            />
          ))}
        </div>
      )}

      {/* Alert detail dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  {selected.title}
                  <SeverityBadge severity={selected.severity} />
                </DialogTitle>
                <DialogDescription>
                  {selected.id} · {selected.source} · {selected.time}
                </DialogDescription>
              </DialogHeader>
              <DialogBody>
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={selected.status} />
                  </div>
                  <p className="text-sm leading-relaxed text-[var(--muted-foreground)]">
                    {selected.description}
                  </p>
                  {selected.response.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">Suggested actions</p>
                      <div className="flex flex-wrap gap-2">
                        {selected.response.map((r) => (
                          <Badge key={r} variant="secondary" className="cursor-pointer">{r}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  <p className="text-[11px] text-[var(--muted-foreground)]">
                    Detection method is defined by the source sensor. This alert has not been verified against live telemetry.
                  </p>
                </div>
              </DialogBody>
              <DialogFooter>
                <Button variant="outline" size="sm" onClick={() => setOpen(false)}>Close</Button>
                <Button variant="gradient" size="sm" onClick={() => setOpen(false)}>Acknowledge</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
