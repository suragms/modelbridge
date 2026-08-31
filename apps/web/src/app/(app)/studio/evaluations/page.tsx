"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEvaluationSuites } from "@/lib/hooks";

export default function StudioEvaluationsPage() {
  const suites = useEvaluationSuites();
  const list = (suites.data as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Evaluation Studio</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Dataset-based testing with objective scorers (exact match, contains, regex, JSON schema).
          </p>
        </div>
        <Link href="/studio/evaluations/datasets" className="text-sm underline">
          Manage Datasets
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evaluation Suites</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {list.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">
              No evaluation suites yet. Create datasets first, then define suites via the API or CLI.
            </p>
          )}
          {list.map((s) => (
            <div key={String(s.id)} className="rounded border px-3 py-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{String(s.name)}</span>
                <Badge variant="outline">{String(s.model ?? "auto")}</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
