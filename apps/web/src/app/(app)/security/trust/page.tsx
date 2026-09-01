"use client";

import { FileBadge, ShieldCheck, AlertTriangle, ExternalLink } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { StatusBadge, StatusType } from "@/components/security/status-badge";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const SAMPLE_LABEL =
  "Sample content — shown for UI review only. We do not claim any certifications or compliance that have not been formally audited and granted.";

// Illustrative posture — each entry explicitly labelled as to whether any claim is asserted.
const CONTROLS = [
  { name: "Data encryption at rest and in transit", status: "enforced" as StatusType, asserted: true, note: "TLS for transit; provider-managed encryption at rest." },
  { name: "Access control & least privilege", status: "enforced" as StatusType, asserted: true, note: "Role-based access scoped to organization." },
  { name: "Prompt & output filtering", status: "enforced" as StatusType, asserted: true, note: "Configurable redaction and masking." },
  { name: "Audit logging", status: "draft" as StatusType, asserted: false, note: "Logging available; retention policy not yet formalized." },
];

const CERTIFICATIONS: { name: string; status: string; note: string }[] = [
  { name: "SOC 2 Type II", status: "Not claimed", note: "An independent audit has not been completed. We will only update this after a formal assessment." },
  { name: "ISO 27001", status: "Not claimed", note: "Certification not yet pursued. Status updated when granted." },
];

export default function TrustCenterPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={FileBadge}
        title="Trust Center"
        description="Transparency about our security posture and independent verifications"
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Security controls */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="h-4 w-4 text-[var(--primary)]" /> Security controls
            </CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-[var(--border)] p-0">
            {CONTROLS.map((c) => (
              <div key={c.name} className="flex items-start justify-between gap-3 px-4 py-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{c.name}</span>
                    {c.asserted && <Badge variant="success" className="text-[10px]">Asserted</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted-foreground)]">{c.note}</p>
                </div>
                <StatusBadge status={c.status} />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Certifications */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <FileBadge className="h-4 w-4 text-[var(--primary)]" /> Compliance & certifications
            </CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-[var(--border)] p-0">
            {CERTIFICATIONS.map((cert) => (
              <div key={cert.name} className="px-4 py-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{cert.name}</span>
                  <Badge variant="outline" className="text-[10px]">{cert.status}</Badge>
                </div>
                <p className="mt-1.5 text-xs text-[var(--muted-foreground)]">{cert.note}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-8">
          <EmptySecurityState
            icon={FileBadge}
            title="Request a security review"
            description="Share this workspace with your security team for a full evidence review. Access is granted only with explicit permission."
            action={
              <a
                href="#"
                onClick={(e) => e.preventDefault()}
                className="inline-flex items-center gap-2 text-sm text-[var(--primary)] hover:underline"
              >
                Learn how we handle your data <ExternalLink className="h-4 w-4" />
              </a>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
