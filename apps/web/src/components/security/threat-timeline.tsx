"use client";

import { cn } from "@/lib/utils";
import { SeverityBadge, Severity } from "./severity-badge";

export interface TimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  description?: string;
  severity?: Severity;
  source?: string;
}

interface ThreatTimelineProps {
  events: TimelineEvent[];
  className?: string;
}

export function ThreatTimeline({ events, className }: ThreatTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
        No events recorded yet.
      </div>
    );
  }

  return (
    <div className={cn("relative space-y-0", className)}>
      <div className="absolute left-[15px] top-2 bottom-2 w-px bg-[var(--border)]" aria-hidden="true" />
      {events.map((event, i) => (
        <div key={event.id} className="relative flex gap-4 pb-6 last:pb-0">
          <div className="relative z-10 mt-1 flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full border-2 border-[var(--border)] bg-[var(--card)]">
            <div
              className={cn(
                "h-2 w-2 rounded-full",
                event.severity === "critical" && "bg-[var(--severity-critical)]",
                event.severity === "high" && "bg-[var(--severity-high)]",
                event.severity === "medium" && "bg-[var(--severity-medium)]",
                event.severity === "low" && "bg-[var(--severity-low)]",
                event.severity === "info" && "bg-[var(--severity-info)]",
                !event.severity && "bg-[var(--muted-foreground)]"
              )}
            />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">{event.title}</span>
              {event.severity && <SeverityBadge severity={event.severity} />}
            </div>
            {event.description && (
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">{event.description}</p>
            )}
            <div className="mt-1.5 flex items-center gap-3 text-[11px] text-[var(--muted-foreground)]">
              <time>{event.timestamp}</time>
              {event.source && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{event.source}</span>
                </>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
