"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface ChartPoint {
  timestamp: string;
  value: number;
}

interface TimeSeriesChartProps {
  data: ChartPoint[];
  label: string;
  valueFormatter?: (v: number) => string;
  emptyMessage?: string;
  color?: string;
}

export function TimeSeriesChart({
  data,
  label,
  valueFormatter = (v) => String(v),
  emptyMessage = "No data available for this period.",
  color = "var(--ring)",
}: TimeSeriesChartProps) {
  if (!data.length) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-[var(--muted-foreground)]">
        {emptyMessage}
      </div>
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    label: d.timestamp ? new Date(d.timestamp).toLocaleDateString() : "",
  }));

  return (
    <div>
      <p className="mb-2 text-xs text-[var(--muted-foreground)]">{label}</p>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
          <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
          <Tooltip
            formatter={(value: number) => [valueFormatter(value), label]}
            contentStyle={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
            }}
          />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
