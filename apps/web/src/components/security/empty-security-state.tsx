"use client";

import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptySecurityStateProps {
  icon?: React.ElementType;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptySecurityState({
  icon: Icon = ShieldCheck,
  title,
  description,
  action,
  className,
}: EmptySecurityStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-[var(--border)] bg-[var(--muted)]/20 py-16 px-6 text-center",
        className
      )}
    >
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand-gradient-soft)]">
        <Icon className="h-6 w-6 text-[var(--primary)]" />
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-[var(--muted-foreground)]">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
