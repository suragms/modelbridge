"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useCreateGovernancePolicy,
  useDeleteGovernancePolicy,
  useGovernancePolicies,
  useUpdateGovernancePolicy,
} from "@/lib/hooks";

const TYPES = ["organization", "model", "provider", "api_key", "request", "response"];
const ACTIONS = ["allow", "warn", "deny", "require_approval", "redact"];
const STATUSES = ["draft", "active", "disabled"];

export default function PoliciesPage() {
  const list = useGovernancePolicies();
  const create = useCreateGovernancePolicy();
  const update = useUpdateGovernancePolicy();
  const del = useDeleteGovernancePolicy();
  const [name, setName] = useState("");
  const [policyType, setPolicyType] = useState("organization");
  const [action, setAction] = useState("deny");
  const [priority, setPriority] = useState("100");
  const [rules, setRules] = useState("{\n  \"conditions\": []\n}");
  const [error, setError] = useState("");

  const save = async () => {
    setError("");
    try {
      await create.mutateAsync({
        name,
        policy_type: policyType,
        action,
        status: "active",
        priority: Number(priority),
        rules: JSON.parse(rules),
      });
      setName("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create policy");
    }
  };

  const policies = list.data ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Policies</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Organization-isolated rules. DENY always overrides ALLOW at the same scope.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create policy</CardTitle>
          <CardDescription>Rules are JSON conditions — not executable code.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 max-w-xl">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Type</Label>
              <Select value={policyType} onChange={(e) => setPolicyType(e.target.value)}>
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Action</Label>
              <Select value={action} onChange={(e) => setAction(e.target.value)}>
                {ACTIONS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Priority (lower runs first)</Label>
            <Input value={priority} onChange={(e) => setPriority(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Rules JSON</Label>
            <textarea
              className="min-h-32 w-full rounded-md border border-[var(--border)] bg-transparent p-2 font-mono text-xs"
              value={rules}
              onChange={(e) => setRules(e.target.value)}
            />
          </div>
          <Button onClick={save} disabled={!name || create.isPending}>
            Create
          </Button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Priority</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {policies.map((p) => (
            <TableRow key={String(p.id)}>
              <TableCell>
                <Link className="underline" href={`/governance/policies/${p.id}`}>
                  {String(p.name)}
                </Link>
              </TableCell>
              <TableCell>{String(p.policy_type)}</TableCell>
              <TableCell>{String(p.action)}</TableCell>
              <TableCell>{String(p.status)}</TableCell>
              <TableCell>{String(p.priority)}</TableCell>
              <TableCell className="space-x-2">
                <Button
                  variant="secondary"
                  onClick={() =>
                    update.mutate({
                      id: String(p.id),
                      body: {
                        status: p.status === "active" ? "disabled" : "active",
                        change_summary: "Toggled status",
                      },
                    })
                  }
                >
                  {p.status === "active" ? "Disable" : "Enable"}
                </Button>
                <Button variant="secondary" onClick={() => del.mutate(String(p.id))}>
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
