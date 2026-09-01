"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFinopsBudgets } from "@/lib/hooks";

export default function FinopsBudgetsPage() {
  const budgets = useFinopsBudgets();
  const list = (budgets.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Budget Management</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Organization, team, and project budgets with configurable thresholds.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Budgets</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No budgets configured.</p>}
          {list.map((b) => (
            <div key={String(b.id)} className="flex justify-between rounded border px-3 py-2 text-sm">
              <div>
                <span className="font-medium">{String(b.name)}</span>
                <p className="text-xs text-[var(--muted-foreground)]">{String(b.scope)} · {String(b.period)}</p>
              </div>
              <div className="text-right">
                <p>${Number(b.amount ?? 0).toFixed(2)} {String(b.currency)}</p>
                <Badge variant="outline">{b.enabled ? "active" : "disabled"}</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
