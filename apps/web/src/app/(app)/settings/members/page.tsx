"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useOrganizationMembers } from "@/lib/hooks";

export default function MembersPage() {
  const membersQuery = useOrganizationMembers();
  const members = (membersQuery.data ?? []) as Array<{
    id: string;
    email: string;
    full_name: string | null;
    role: string;
  }>;

  return (
    <div className="space-y-8">
      <div>
        <Link href="/settings/organization" className="text-sm text-[var(--ring)] hover:underline">
          ← Organization settings
        </Link>
        <h1 className="mt-2 text-2xl font-bold">Members</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Organization members and roles. Invite via API token (no email delivery).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Team</CardTitle>
        </CardHeader>
        <CardContent>
          {membersQuery.isLoading ? (
            <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>
          ) : members.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">No members found.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Role</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>{m.email}</TableCell>
                    <TableCell>{m.full_name ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{m.role}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
