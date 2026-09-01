"use client";

import { useState } from "react";
import { ChevronDown, FileText, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export interface EvidenceItem {
  id: string;
  title: string;
  type: string;
  timestamp?: string;
  description?: string;
  url?: string;
  sensitive?: boolean;
}

interface EvidencePanelProps {
  items: EvidenceItem[];
  className?: string;
}

export function EvidencePanel({ items, className }: EvidencePanelProps) {
  const [expanded, setExpanded] = useState(true);

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 p-4 text-center text-sm text-[var(--muted-foreground)]">
        No evidence collected yet.
      </div>
    );
  }

  return (
    <div className={cn("rounded-xl border bg-[var(--card)] overflow-hidden", className)}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold hover:bg-[var(--muted)]/30 transition-colors"
      >
        <span className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-[var(--muted-foreground)]" />
          Evidence ({items.length})
        </span>
        <ChevronDown
          className={cn("h-4 w-4 text-[var(--muted-foreground)] transition-transform", !expanded && "-rotate-90")}
        />
      </button>
      {expanded && (
        <div className="divide-y border-t border-[var(--border)]">
          {items.map((item) => (
            <div key={item.id} className="flex items-start gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{item.title}</span>
                  <Badge variant="secondary" className="text-[10px]">
                    {item.type}
                  </Badge>
                  {item.sensitive && (
                    <Badge variant="warning" className="text-[10px]">Sensitive</Badge>
                  )}
                </div>
                {item.description && (
                  <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                    {item.sensitive ? "[REDACTED]" : item.description}
                  </p>
                )}
                {item.timestamp && (
                  <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">{item.timestamp}</p>
                )}
              </div>
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 text-[var(--muted-foreground)] hover:text-[var(--primary)] transition-colors"
                  aria-label={`Open ${item.title}`}
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
