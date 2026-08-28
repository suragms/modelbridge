"use client";

import { useState } from "react";
import {
  GitBranch,
  Play,
  Plus,
  Pencil,
  Trash2,
  FlaskConical,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
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
  useCreateRoutingPolicy,
  useDeleteRoutingPolicy,
  useRoutingPolicies,
  useTestRouting,
  useUpdateRoutingPolicy,
} from "@/lib/hooks";
import type {
  RoutingPolicy,
  RoutingStrategy,
  RoutingTestResponse,
} from "@/lib/types";

const STRATEGIES: { value: RoutingStrategy; label: string }[] = [
  { value: "auto", label: "Auto (balanced)" },
  { value: "balanced", label: "Balanced" },
  { value: "priority", label: "Priority" },
  { value: "cheapest", label: "Cheapest" },
  { value: "fastest", label: "Fastest" },
  { value: "quality", label: "Quality" },
  { value: "local_only", label: "Local only" },
  { value: "privacy_first", label: "Privacy first" },
  { value: "round_robin", label: "Round robin" },
  { value: "least_latency", label: "Least latency" },
];

function PolicyDialog({
  open,
  onOpenChange,
  policy,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  policy: RoutingPolicy | null;
  onSubmit: (data: {
    name: string;
    description: string | null;
    strategy: RoutingStrategy;
    config: Record<string, unknown> | null;
    is_default: boolean;
  }) => void;
}) {
  const [name, setName] = useState(policy?.name ?? "");
  const [description, setDescription] = useState(policy?.description ?? "");
  const [strategy, setStrategy] = useState<RoutingStrategy>(policy?.strategy ?? "auto");
  const [isDefault, setIsDefault] = useState(policy?.is_default ?? false);

  // Reset state when the dialog opens for a different policy.
  const [lastKey, setLastKey] = useState<string | null>(null);
  const key = policy?.id ?? "new";
  if (key !== lastKey) {
    setLastKey(key);
    setName(policy?.name ?? "");
    setDescription(policy?.description ?? "");
    setStrategy(policy?.strategy ?? "auto");
    setIsDefault(policy?.is_default ?? false);
  }

  const submit = () => {
    onSubmit({
      name,
      description: description || null,
      strategy,
      config: policy?.config ?? {},
      is_default: isDefault,
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{policy ? "Edit Policy" : "New Routing Policy"}</DialogTitle>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="policy-name">Name</Label>
            <Input
              id="policy-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production default"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="policy-desc">Description</Label>
            <Input
              id="policy-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="policy-strategy">Strategy</Label>
            <Select
              id="policy-strategy"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as RoutingStrategy)}
            >
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
            />
            Set as default policy
          </label>
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!name.trim()}>
            {policy ? "Save" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TestResultPanel({ result }: { result: RoutingTestResponse }) {
  const filteredOut = result.candidates.filter((c) => c.eligible === false);
  const debug = result.debug ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 p-3">
        <Badge variant="secondary">Strategy: {result.strategy}</Badge>
        {result.requested_capabilities && result.requested_capabilities.length > 0 && (
          <Badge variant="secondary">
            Caps: {result.requested_capabilities.join(", ")}
          </Badge>
        )}
        <span className="text-sm">{result.reason}</span>
        {result.selected && (
          <span className="ml-auto text-sm">
            Selected: <span className="font-semibold">{result.selected.model_name}</span>
            <span className="text-[var(--muted-foreground)]">
              {" "}
              via {result.selected.provider_name}
            </span>
          </span>
        )}
      </div>

      {result.selected && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-[var(--border)] p-3">
            <p className="text-xs text-[var(--muted-foreground)]">Model</p>
            <p className="truncate text-sm font-medium">{result.selected.model_name}</p>
          </div>
          <div className="rounded-lg border border-[var(--border)] p-3">
            <p className="text-xs text-[var(--muted-foreground)]">Provider</p>
            <p className="truncate text-sm font-medium">{result.selected.provider_name}</p>
          </div>
          <div className="rounded-lg border border-[var(--border)] p-3">
            <p className="text-xs text-[var(--muted-foreground)]">Score</p>
            <p className="text-sm font-medium">{result.selected.score.toFixed(3)}</p>
          </div>
          <div className="rounded-lg border border-[var(--border)] p-3">
            <p className="text-xs text-[var(--muted-foreground)]">Latency</p>
            <p className="text-sm font-medium">{result.selected.latency_ms.toFixed(0)} ms</p>
          </div>
        </div>
      )}

      <div>
        <p className="mb-2 text-sm font-medium">Candidate ranking</p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>Model</TableHead>
              <TableHead>Provider</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Latency</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.filtered.map((c, i) => (
              <TableRow key={c.model_id}>
                <TableCell>{i + 1}</TableCell>
                <TableCell className="font-medium">{c.model_name}</TableCell>
                <TableCell className="text-[var(--muted-foreground)]">
                  {c.provider_name}
                  {c.is_local && <Badge className="ml-2" variant="secondary">local</Badge>}
                </TableCell>
                <TableCell>{c.score.toFixed(3)}</TableCell>
                <TableCell>{c.latency_ms.toFixed(0)} ms</TableCell>
              </TableRow>
            ))}
            {result.filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-[var(--muted-foreground)]">
                  No eligible candidates found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {result.fallback_order.length > 0 && (
        <div>
          <p className="mb-1 text-sm font-medium">Fallback order</p>
          <p className="text-sm text-[var(--muted-foreground)]">
            {result.fallback_order.join(" → ")}
          </p>
        </div>
      )}

      {(debug.length > 0 || filteredOut.length > 0) && (
        <div>
          <p className="mb-2 text-sm font-medium">Capability debugging</p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Model</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(debug.length > 0 ? debug : filteredOut).map((entry) => {
                const eligible =
                  "eligible" in entry
                    ? entry.eligible
                    : (entry as { eligible?: boolean }).eligible !== false;
                const reason =
                  "filter_reason" in entry
                    ? entry.filter_reason
                    : (entry as { filter_reason?: string | null }).filter_reason;
                const modelName =
                  "model_name" in entry
                    ? entry.model_name
                    : (entry as { model_name: string }).model_name;
                const providerName =
                  "provider_name" in entry
                    ? entry.provider_name
                    : (entry as { provider_name: string }).provider_name;
                const key =
                  "model_id" in entry
                    ? String(entry.model_id)
                    : (entry as { model_id: string }).model_id;
                return (
                  <TableRow key={key}>
                    <TableCell className="font-medium">{modelName}</TableCell>
                    <TableCell>{providerName}</TableCell>
                    <TableCell>
                      <Badge variant={eligible ? "success" : "secondary"}>
                        {eligible ? "Compatible" : "Filtered"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-[var(--muted-foreground)]">
                      {reason ?? (eligible ? "—" : "Incompatible")}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

export default function RoutingPage() {
  const policiesQuery = useRoutingPolicies();
  const createPolicy = useCreateRoutingPolicy();
  const updatePolicy = useUpdateRoutingPolicy();
  const deletePolicy = useDeleteRoutingPolicy();
  const testRouting = useTestRouting();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<RoutingPolicy | null>(null);

  // Test panel state
  const [requestedModel, setRequestedModel] = useState("auto");
  const [testStrategy, setTestStrategy] = useState<RoutingStrategy | "default">("default");
  const [policyName, setPolicyName] = useState<string | "">("");
  const [requiredCaps, setRequiredCaps] = useState<string[]>([]);
  const [result, setResult] = useState<RoutingTestResponse | null>(null);
  const [testError, setTestError] = useState("");

  const CAP_OPTIONS = ["chat", "streaming", "tools", "vision", "embeddings", "json_mode"];

  const policies = policiesQuery.data ?? [];

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (p: RoutingPolicy) => {
    setEditing(p);
    setDialogOpen(true);
  };

  const handleSubmit = async (data: {
    name: string;
    description: string | null;
    strategy: RoutingStrategy;
    config: Record<string, unknown> | null;
    is_default: boolean;
  }) => {
    if (editing) {
      await updatePolicy.mutateAsync({ id: editing.id, body: data });
    } else {
      await createPolicy.mutateAsync(data);
    }
  };

  const handleDelete = async (p: RoutingPolicy) => {
    if (!confirm(`Delete routing policy "${p.name}"?`)) return;
    try {
      await deletePolicy.mutateAsync(p.id);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleTest = async () => {
    setTestError("");
    setResult(null);
    try {
      const strategy = testStrategy === "default" ? undefined : testStrategy;
      const res = await testRouting.mutateAsync({
        requested_model: requestedModel,
        strategy,
        policy_name: policyName || undefined,
        required_capabilities: requiredCaps.length > 0 ? requiredCaps : undefined,
      });
      setResult(res);
    } catch (e) {
      setTestError(e instanceof Error ? e.message : "Routing test failed");
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Routing</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Model selection strategies, policies, and fallbacks
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> New Policy
        </Button>
      </div>

      {/* Policies */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <GitBranch className="h-4 w-4" /> Routing Policies
          </CardTitle>
          <CardDescription>
            Named policies that control how the gateway picks a model.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {policiesQuery.isLoading ? (
            <p className="py-8 text-center text-[var(--muted-foreground)]">Loading…</p>
          ) : policies.length === 0 ? (
            <div className="py-12 text-center text-[var(--muted-foreground)]">
              No routing policies yet. Create one to control model selection.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Default</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{p.strategy}</Badge>
                    </TableCell>
                    <TableCell>
                      {p.is_default ? (
                        <Badge variant="success">default</Badge>
                      ) : (
                        <span className="text-[var(--muted-foreground)]">—</span>
                      )}
                    </TableCell>
                    <TableCell className="max-w-[280px] truncate text-[var(--muted-foreground)]">
                      {p.description ?? "—"}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="sm" title="Edit" onClick={() => openEdit(p)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          title="Delete"
                          className="text-red-600 hover:bg-red-50"
                          disabled={p.is_default}
                          onClick={() => handleDelete(p)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Routing test */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FlaskConical className="h-4 w-4" /> Test Routing
          </CardTitle>
          <CardDescription>
            Preview which model the gateway would select without sending a request.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="test-model">Requested model</Label>
              <Input
                id="test-model"
                value={requestedModel}
                onChange={(e) => setRequestedModel(e.target.value)}
                className="w-52"
                placeholder='e.g. "auto" or a model id'
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="test-strategy">Strategy override</Label>
              <Select
                id="test-strategy"
                value={testStrategy}
                onChange={(e) => setTestStrategy(e.target.value as RoutingStrategy | "default")}
                className="w-52"
              >
                <option value="default">(use policy default)</option>
                {STRATEGIES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="test-policy">Policy</Label>
              <Select
                id="test-policy"
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
                className="w-52"
              >
                <option value="">(default policy)</option>
                {policies.map((p) => (
                  <option key={p.id} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <Button onClick={handleTest} disabled={testRouting.isPending}>
              <Play className="h-4 w-4" />
              {testRouting.isPending ? "Testing…" : "Run test"}
            </Button>
          </div>

          <div className="mt-4 space-y-2">
            <Label>Required capabilities (optional)</Label>
            <div className="flex flex-wrap gap-2">
              {CAP_OPTIONS.map((cap) => {
                const active = requiredCaps.includes(cap);
                return (
                  <button
                    key={cap}
                    type="button"
                    onClick={() =>
                      setRequiredCaps((prev) =>
                        active ? prev.filter((c) => c !== cap) : [...prev, cap]
                      )
                    }
                    className={`rounded-full border px-3 py-1 text-sm ${
                      active
                        ? "border-[var(--ring)] bg-[var(--muted)]"
                        : "border-[var(--border)] text-[var(--muted-foreground)]"
                    }`}
                  >
                    {cap}
                  </button>
                );
              })}
            </div>
          </div>

          {testError && <p className="mt-4 text-sm text-red-600">{testError}</p>}

          {result && (
            <div className="mt-6">
              <TestResultPanel result={result} />
            </div>
          )}
        </CardContent>
      </Card>

      <PolicyDialog
        open={dialogOpen}
        onOpenChange={(o) => {
          setDialogOpen(o);
          if (!o) setEditing(null);
        }}
        policy={editing}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
