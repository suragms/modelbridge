"use client";

import { BarChart3, ShieldAlert, AlertTriangle, Timer } from "lucide-react";

import { SecurityHeader } from "@/components/security/security-header";
import { SeverityBadge, Severity } from "@/components/security/severity-badge";
import { SecurityMetricCard } from "@/components/security/security-metric-card";
import { EmptySecurityState } from "@/components/security/empty-security-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TimeSeriesChart } from "@/components/charts/time-series-chart";

const SAMPLE_LABEL = "Sample data — shown for UI review only. No live telemetry is connected.";

// Illustrative detection trend (sample only).
const DETECTION_TREND = [
  { timestamp: "2026-08-25", value: 6 },
  { timestamp: "2026-08-26", value: 9 },
  { timestamp: "2026-08-27", value: 5 },
  { timestamp: "2026-08-28", value: 11 },
  { timestamp: "2026-08-29", value: 8 },
  { timestamp: "2026-08-30", value: 13 },
  { timestamp: "2026-08-31", value: 7 },
];

const SEVERITY_SPLIT: { severity: Severity; count: number }[] = [
  { severity: "critical", count: 3 },
  { severity: "high", count: 11 },
  { severity: "medium", count: 19 },
  { severity: "low", count: 24 },
  { severity: "info", count: 31 },
];

export default function SecurityAnalyticsPage() {
  const total = SEVERITY_SPLIT.reduce((s, x) => s + x.count, 0);

  return (
    <div className="space-y-8 animate-fade-in">
      <SecurityHeader
        icon={BarChart3}
        title="Security Analytics"
        description="Trends and metrics across threat detection, alerts, and response"
        actions={
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" /> 90-day window
          </div>
        }
      />

      <div className="flex items-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--severity-medium-bg)] px-4 py-2.5 text-xs text-[var(--muted-foreground)]">
        <AlertTriangle className="h-4 w-4 text-[var(--severity-medium)]" />
        {SAMPLE_LABEL}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 stagger-children">
        <SecurityMetricCard icon={ShieldAlert} label="Detections (90d)" value={88} gradient="from-red-500 to-rose-400" />
        <SecurityMetricCard icon={Timer} label="Mean time to respond" value="42m" gradient="from-amber-500 to-orange-400" />
        <SecurityMetricCard icon={BarChart3} label="False positive rate" value="9%" trend="down" trendValue="−3%" gradient="from-emerald-500 to-green-400" />
        <SecurityMetricCard icon={ShieldAlert} label="Critical detections" value={3} gradient="from-slate-500 to-gray-400" />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="text-sm font-semibold">Detections over time</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <TimeSeriesChart data={DETECTION_TREND} label="Detections" color="var(--severity-high)" />
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader className="border-b border-[var(--border)] bg-[var(--muted)]/30 py-3">
            <CardTitle className="text-sm font-semibold">Detections by severity</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-4">
              {SEVERITY_SPLIT.map((s) => {
                const pct = (s.count / total) * 100;
                return (
                  <div key={s.severity}>
                    <div className="flex items-center justify-between mb-1.5">
                      <SeverityBadge severity={s.severity} />
                      <span className="text-xs font-semibold">{s.count} ({pct.toFixed(0)}%)</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${pct}%`,
                          background: `var(--severity-${s.severity})`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-8">
          <EmptySecurityState
            icon={BarChart3}
            title="Deeper trend analysis coming soon"
            description="Correlation, anomaly baselines, and adversarial-typing dashboards will be available once live telemetry is connected."
          />
        </CardContent>
      </Card>
    </div>
  );
}
