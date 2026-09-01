"use client";

import { cn } from "@/lib/utils";

interface SecurityHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  icon?: React.ElementType;
  className?: string;
}

export function SecurityHeader({
  title,
  description,
  actions,
  icon: Icon,
  className,
}: SecurityHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between", className)}>
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--brand-gradient-soft)]">
            <Icon className="h-4.5 w-4.5 text-[var(--primary)]" />
          </div>
        )}
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          {description && (
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
