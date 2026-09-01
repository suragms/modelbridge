"use client";

import { cn } from "@/lib/utils";

interface CategoryScore {
  label: string;
  score: number;
  maxScore?: number;
}

interface SecurityPostureCardProps {
  overallScore: number;
  maxScore?: number;
  categories: CategoryScore[];
  className?: string;
}

function getScoreColor(score: number, max: number): string {
  const pct = (score / max) * 100;
  if (pct >= 80) return "text-emerald-600 dark:text-emerald-400";
  if (pct >= 60) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

function getBarColor(score: number, max: number): string {
  const pct = (score / max) * 100;
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 60) return "bg-amber-500";
  return "bg-red-500";
}

export function SecurityPostureCard({
  overallScore,
  maxScore = 100,
  categories,
  className,
}: SecurityPostureCardProps) {
  return (
    <div className={cn("rounded-xl border bg-[var(--card)] p-6 shadow-sm", className)}>
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold">Security Posture</h3>
        <div className={cn("text-3xl font-bold", getScoreColor(overallScore, maxScore))}>
          {overallScore}
          <span className="text-sm font-normal text-[var(--muted-foreground)]">/{maxScore}</span>
        </div>
      </div>

      <div className="space-y-4">
        {categories.map((cat) => {
          const pct = (cat.score / (cat.maxScore ?? maxScore)) * 100;
          return (
            <div key={cat.label}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-[var(--muted-foreground)]">{cat.label}</span>
                <span className="text-xs font-semibold">
                  {cat.score}/{cat.maxScore ?? maxScore}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                <div
                  className={cn("h-full rounded-full transition-all duration-500", getBarColor(cat.score, cat.maxScore ?? maxScore))}
                  style={{ width: `${pct}%` }}
                  role="progressbar"
                  aria-valuenow={cat.score}
                  aria-valuemin={0}
                  aria-valuemax={cat.maxScore ?? maxScore}
                  aria-label={`${cat.label}: ${cat.score} out of ${cat.maxScore ?? maxScore}`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
