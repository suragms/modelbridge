"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useBudgetAlerts, useOrganizationSettings, useUpdateOrganizationSettings } from "@/lib/hooks";

export default function OrganizationSettingsPage() {
  const settingsQuery = useOrganizationSettings();
  const alertsQuery = useBudgetAlerts();
  const updateSettings = useUpdateOrganizationSettings();
  const settings = settingsQuery.data as Record<string, number | null> | undefined;

  const [rateMinute, setRateMinute] = useState("");
  const [tokenLimit, setTokenLimit] = useState("");
  const [budget, setBudget] = useState("");
  const [saved, setSaved] = useState("");

  const loadIntoForm = () => {
    if (!settings) return;
    setRateMinute(String(settings.rate_limit_per_minute ?? 100));
    setTokenLimit(settings.monthly_token_limit != null ? String(settings.monthly_token_limit) : "");
    setBudget(settings.monthly_budget_usd != null ? String(settings.monthly_budget_usd) : "");
  };

  if (settings && !rateMinute) loadIntoForm();

  const save = async () => {
    setSaved("");
    await updateSettings.mutateAsync({
      rate_limit_per_minute: Number(rateMinute),
      monthly_token_limit: tokenLimit ? Number(tokenLimit) : null,
      monthly_budget_usd: budget ? Number(budget) : null,
    });
    setSaved("Settings saved.");
  };

  const alerts = Array.isArray(alertsQuery.data)
    ? alertsQuery.data
    : ((alertsQuery.data as { alerts?: unknown[] })?.alerts ?? []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Organization Settings</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Rate limits, quotas, and budgets for the active organization
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Limits</CardTitle>
          <CardDescription>
            Budget values use estimated cost data — not exact provider billing.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 max-w-md">
          <div className="space-y-1.5">
            <Label>Requests per minute</Label>
            <Input value={rateMinute} onChange={(e) => setRateMinute(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Monthly token quota (empty = unlimited)</Label>
            <Input value={tokenLimit} onChange={(e) => setTokenLimit(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Monthly budget USD (empty = unlimited)</Label>
            <Input value={budget} onChange={(e) => setBudget(e.target.value)} />
          </div>
          <Button onClick={save} disabled={updateSettings.isPending}>
            {updateSettings.isPending ? "Saving…" : "Save settings"}
          </Button>
          {saved && <p className="text-sm text-green-600">{saved}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Budget alerts</CardTitle>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">No budget alerts recorded.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {(alerts as Array<{ message: string; created_at: string }>).map((a, i) => (
                <li key={i} className="rounded border border-[var(--border)] p-3">
                  {a.message}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Link href="/settings/members" className="text-sm text-[var(--ring)] hover:underline">
        Manage members →
      </Link>
    </div>
  );
}
