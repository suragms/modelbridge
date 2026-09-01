"use client";

import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface SecurityMetricCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  trend?: "up" | "down" | "flat";
  trendValue?: string;
  gradient?: string;
  className?: string;
}

export function SecurityMetricCard({
  icon: Icon,
  label,
  value,
  trend,
  trendValue,
  gradient = "from-blue-500 to-cyan-400",
  className,
}: SecurityMetricCardProps) {
  return (
    <div className={cn("card-interactive group p-5", className)}>
      <div className="flex items-center justify-between">
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br shadow-sm transition-transform duration-200 group-hover:scale-110",
            gradient
          )}
        >
          <Icon className="h-4 w-4 text-white" />
        </div>
        {trend && trendValue && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 text-[11px] font-medium",
              trend === "up" && "text-emerald-600 dark:text-emerald-400",
              trend === "down" && "text-red-600 dark:text-red-400",
              trend === "flat" && "text-[var(--muted-foreground)]"
            )}
          >
            {trend === "up" && <ArrowUpRight className="h-3 w-3" />}
            {trend === "down" && <ArrowDownRight className="h-3 w-3" />}
            {trend === "flat" && <Minus className="h-3 w-3" />}
            {trendValue}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-2xl font-bold tracking-tight">{value}</p>
        <p className="mt-1 text-xs font-medium text-[var(--muted-foreground)]">{label}</p>
      </div>
    </div>
  );
}
