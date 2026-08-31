"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useGovernanceSettings, useUpdateGovernanceSettings } from "@/lib/hooks";

const TOGGLES: { key: string; label: string }[] = [
  { key: "pii_detection_enabled", label: "PII detection" },
  { key: "secret_detection_enabled", label: "Secret detection" },
  { key: "redact_prompts", label: "Redact prompts before provider call" },
  { key: "redact_responses", label: "Redact responses" },
  { key: "block_on_secret", label: "Block when secrets are detected" },
  { key: "block_sensitive_to_cloud", label: "Keep sensitive requests off cloud providers" },
  { key: "require_local_for_high_risk", label: "High risk → local providers only" },
  { key: "allow_cloud_providers", label: "Allow cloud providers" },
  { key: "allow_local_providers", label: "Allow local providers" },
  { key: "content_safety_enabled", label: "Heuristic content safety" },
  { key: "approval_enabled", label: "Approval workflow" },
];

export default function DataProtectionPage() {
  const query = useGovernanceSettings();
  const update = useUpdateGovernanceSettings();
  const [form, setForm] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState("");

  useEffect(() => {
    if (query.data) {
      const next: Record<string, boolean> = {};
      for (const t of TOGGLES) {
        next[t.key] = Boolean(query.data[t.key]);
      }
      setForm(next);
    }
  }, [query.data]);

  const save = async () => {
    setSaved("");
    await update.mutateAsync(form);
    setSaved("Saved.");
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Data protection</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Heuristic detection only. False positives and false negatives are expected. Secret values
          are never written to governance logs.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Detection and handling</CardTitle>
          <CardDescription>Secure defaults: PII/secret detection on, prompt redaction off.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {TOGGLES.map((t) => (
            <label key={t.key} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(form[t.key])}
                onChange={(e) => setForm({ ...form, [t.key]: e.target.checked })}
              />
              {t.label}
            </label>
          ))}
          <Button onClick={save} disabled={update.isPending}>
            Save
          </Button>
          {saved && <p className="text-sm text-green-600">{saved}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
