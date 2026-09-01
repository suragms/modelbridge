"use client";

import { cn } from "@/lib/utils";
import { SeverityBadge, Severity } from "./severity-badge";
import { StatusBadge, StatusType } from "./status-badge";

interface AlertCardProps {
  id: string;
  title: string;
  description?: string;
  severity: Severity;
  status: StatusType;
  source?: string;
  timestamp?: string;
  onClick?: () => void;
  className?: string;
}

export function AlertCard({
  id,
  title,
  description,
  severity,
  status,
  source,
  timestamp,
  onClick,
  className,
}: AlertCardProps) {
  const isClickable = Boolean(onClick);

  return (
    <div
      className={cn(
        "rounded-xl border bg-[var(--card)] p-4 shadow-sm transition-all duration-200",
        isClickable && "cursor-pointer hover:shadow-md hover:border-[var(--primary)]/30",
        className
      )}
      onClick={onClick}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      aria-label={`Alert: ${title}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-semibold truncate">{title}</h4>
            <SeverityBadge severity={severity} />
            <StatusBadge status={status} />
          </div>
          {description && (
            <p className="mt-1.5 text-xs text-[var(--muted-foreground)] line-clamp-2">
              {description}
            </p>
          )}
          <div className="mt-2 flex items-center gap-3 text-[11px] text-[var(--muted-foreground)]">
            <span className="font-mono">{id}</span>
            {source && (
              <>
                <span aria-hidden="true">·</span>
                <span>{source}</span>
              </>
            )}
            {timestamp && (
              <>
                <span aria-hidden="true">·</span>
                <time>{timestamp}</time>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
