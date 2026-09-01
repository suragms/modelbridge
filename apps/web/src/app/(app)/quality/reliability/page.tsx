"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQualityScorecards } from "@/lib/hooks";

export default function QualityReliabilityPage() {
  const scorecards = useQualityScorecards();
  const list = (scorecards.data as Array<Record<string, unknown>>) ?? [];
  const reliability = list.find((s) => s.type === "reliability") ?? list[0];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Reliability Scorecard</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Explainable metrics with formula, inputs, and documented limitations.
        </p>
      </div>
      {!reliability && (
        <p className="text-sm text-[var(--muted-foreground)]">No scorecard computed yet.</p>
      )}
      {reliability && (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">Overall</CardTitle></CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">
                {reliability.overall_score != null ? Number(reliability.overall_score).toFixed(2) : "—"}
              </p>
              <p className="mt-2 text-xs text-[var(--muted-foreground)]">{String(reliability.formula)}</p>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">{String(reliability.limitations)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">Dimensions</CardTitle></CardHeader>
            <CardContent>
              <pre className="overflow-x-auto text-xs">{JSON.stringify(reliability.dimensions, null, 2)}</pre>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
