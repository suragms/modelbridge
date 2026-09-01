"use client";

import {
  AlertTriangle,
  CircleAlert,
  Info,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

interface SeverityBadgeProps {
  severity: Severity;
  size?: "sm" | "md";
  showIcon?: boolean;
  className?: string;
}

const SEVERITY_CONFIG: Record<
  Severity,
  {
    label: string;
    icon: React.ElementType;
    bg: string;
    text: string;
    border: string;
  }
> = {
  critical: {
    label: "Critical",
    icon: ShieldAlert,
    bg: "bg-[var(--severity-critical-bg)]",
    text: "text-[var(--severity-critical)]",
    border: "border-[var(--severity-critical)]/20",
  },
  high: {
    label: "High",
    icon: CircleAlert,
    bg: "bg-[var(--severity-high-bg)]",
    text: "text-[var(--severity-high)]",
    border: "border-[var(--severity-high)]/20",
  },
  medium: {
    label: "Medium",
    icon: AlertTriangle,
    bg: "bg-[var(--severity-medium-bg)]",
    text: "text-[var(--severity-medium)]",
    border: "border-[var(--severity-medium)]/20",
  },
  low: {
    label: "Low",
    icon: ShieldCheck,
    bg: "bg-[var(--severity-low-bg)]",
    text: "text-[var(--severity-low)]",
    border: "border-[var(--severity-low)]/20",
  },
  info: {
    label: "Info",
    icon: Info,
    bg: "bg-[var(--severity-info-bg)]",
    text: "text-[var(--severity-info)]",
    border: "border-[var(--severity-info)]/20",
  },
};

export function SeverityBadge({
  severity,
  size = "sm",
  showIcon = true,
  className,
}: SeverityBadgeProps) {
  const config = SEVERITY_CONFIG[severity];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium",
        config.bg,
        config.text,
        config.border,
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs",
        className
      )}
      role="status"
      aria-label={`Severity: ${config.label}`}
    >
      {showIcon && <Icon className={cn(size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5")} />}
      {config.label}
    </span>
  );
}
