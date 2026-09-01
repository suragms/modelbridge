"use client";

import { useState } from "react";
import { FileCheck, Plus, AlertTriangle, Pencil } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogFooter,
} from "@/components/ui/dialog";

const SAMPLE_LABEL = "Sample data — shown for UI review only.";

interface Policy {
  id: string;
  name: string;
  scope: string;
  severity: Severity;
  status: StatusType;
  updated: string;
  appliesTo: string;
}

const POLICIES: Policy[] = [
  { id: "PLC-01", name: "Prompt injection — block direct", scope: "All traffic", severity: "critical", status: "enforced", updated: "2d ago", appliesTo: "chat/completions" },
  { id: "PLC-02", name: "Mask PII in responses", scope: "Production", severity: "high", status: "enforced", updated: "5d ago", appliesTo: "all models" },
  { id: "PLC-03", name: "Redact secrets in logs", scope: "All traffic", severity: "high", status: "enforced", updated: "1w ago", appliesTo: "logging" },
  { id: "PLC-04", name: "Rate-limit anonymous keys", scope: "Public", severity: "medium", status: "draft", updated: "3d ago", appliesTo: "default keys" },
  { id: "PLC-05", name: "Reject tool-use on untrusted context", scope: "Tool calls", severity: "medium", status: "exempt", updated: "2w ago", appliesTo: "agents" },
];

export default function PoliciesPage() {
  const [selected, setSelected] = useState<Policy | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);

  const openEditor = (p: Policy | null) => {
    setSelected(p);
    setEditorOpen(true);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={FileCheck}
        title="Security Policies"
        description="Automated controls applied to gateway traffic and model behavior"
        actions={
          <Button variant="gradient" size="sm" onClick={() => openEditor(null)} className="hidden sm:inline-flex">
            <Plus className="h-4 w-4" /> New policy
          </Button>
        }
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {POLICIES.length === 0 ? (
            <EmptySecurityState
              icon={FileCheck}
              title="No policies defined"
              description="Create your first policy to automate enforcement across gateway traffic and model behavior."
              action={
                <Button variant="gradient" onClick={() => openEditor(null)}>
                  <Plus className="h-4 w-4" /> Create policy
                </Button>
              }
            />
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {POLICIES.map((p) => (
                <div key={p.id} className="flex items-center justify-between gap-3 px-4 py-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{p.name}</span>
                      <SeverityBadge severity={p.severity} />
                      <StatusBadge status={p.status} />
                    </div>
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                      {p.id} · scope: {p.scope} · applies to <code className="rounded bg-[var(--muted)] px-1 font-mono text-[11px]">{p.appliesTo}</code> · updated {p.updated}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => openEditor(p)} aria-label={`Edit ${p.name}`}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Policy editor */}
      <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selected ? `Edit: ${selected.name}` : "Create new policy"}</DialogTitle>
            <DialogDescription>
              Define the automated control applied to gateway traffic.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="pname" className="text-sm font-medium">Policy name</Label>
                <Input id="pname" defaultValue={selected?.name ?? ""} placeholder="e.g. Block prompt injection" className="h-10" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pscope" className="text-sm font-medium">Scope</Label>
                <Input id="pscope" defaultValue={selected?.scope ?? ""} placeholder="e.g. All traffic" className="h-10" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="penforce" className="text-sm font-medium">Enforcement</Label>
                <Input id="penforce" defaultValue={selected?.appliesTo ?? ""} placeholder="e.g. chat/completions" className="h-10" />
              </div>
              <p className="text-[11px] text-[var(--muted-foreground)]">
                Policies are illustrative in this sample build. Changes are not persisted to a live backend.
              </p>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setEditorOpen(false)}>Cancel</Button>
            <Button variant="gradient" size="sm" onClick={() => setEditorOpen(false)}>
              {selected ? "Save changes" : "Create policy"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
