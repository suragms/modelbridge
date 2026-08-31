"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFleetInstance } from "@/lib/hooks";

export default function FleetInstancePage() {
  const params = useParams();
  const id = String(params.id);
  const inst = useFleetInstance(id);
  const data = inst.data as Record<string, unknown> | undefined;

  if (inst.isLoading) return <p className="text-sm">Loading…</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/fleet" className="text-sm underline">
          ← Fleet
        </Link>
        <h1 className="mt-2 text-2xl font-bold">{String(data?.name ?? id)}</h1>
        <Badge className="mt-2" variant="outline">
          {String(data?.status)}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Instance details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Endpoint: {String(data?.endpoint)}</p>
          <p>Version: {String(data?.version ?? "—")}</p>
          <p>Environment: {String(data?.environment_kind ?? "—")}</p>
          <p>Last seen: {data?.last_seen_at ? String(data.last_seen_at) : "never"}</p>
        </CardContent>
      </Card>
    </div>
  );
}
