"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFinopsForecast } from "@/lib/hooks";

export default function FinopsForecastPage() {
  const forecast = useFinopsForecast();
  const data = forecast.data as Record<string, unknown> | undefined;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Cost Forecast</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Projections based on historical data — not a billing guarantee.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Forecast</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="text-2xl font-semibold">
            {data?.forecast_amount != null ? `$${Number(data.forecast_amount).toFixed(2)}` : "—"}
          </p>
          <p>Method: {String(data?.method ?? "n/a")}</p>
          <p>Confidence: {String(data?.confidence ?? "n/a")}</p>
          <p>Cost type: {String(data?.cost_type ?? "unknown")}</p>
          <p className="text-xs text-[var(--muted-foreground)]">{String(data?.limitations ?? "")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
