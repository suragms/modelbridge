"use client";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useGovernanceApprovals, useReviewApproval } from "@/lib/hooks";

export default function ApprovalsPage() {
  const list = useGovernanceApprovals();
  const review = useReviewApproval();
  const rows = list.data ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Approvals</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Requests are not executed automatically after approval. Replay the original request with
          header X-ModelBridge-Approval-ID.
        </p>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Status</TableHead>
            <TableHead>Risk</TableHead>
            <TableHead>Classification</TableHead>
            <TableHead>Model</TableHead>
            <TableHead>Policy</TableHead>
            <TableHead>Created</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((a) => (
            <TableRow key={String(a.id)}>
              <TableCell>{String(a.status)}</TableCell>
              <TableCell>{String(a.risk_level ?? "—")}</TableCell>
              <TableCell>{String(a.classification ?? "—")}</TableCell>
              <TableCell>{String(a.requested_model ?? "—")}</TableCell>
              <TableCell>{String(a.matched_policy_name ?? "—")}</TableCell>
              <TableCell>{String(a.created_at)}</TableCell>
              <TableCell className="space-x-2">
                {a.status === "pending" && (
                  <>
                    <Button
                      size="sm"
                      onClick={() => review.mutate({ id: String(a.id), action: "approve" })}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => review.mutate({ id: String(a.id), action: "reject" })}
                    >
                      Reject
                    </Button>
                  </>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
