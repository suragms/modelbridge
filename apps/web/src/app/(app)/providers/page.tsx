"use client";

import { useState } from "react";
import {
  Boxes,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  Zap,
} from "lucide-react";

import { ProviderDialog } from "@/components/providers/provider-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useCreateProvider,
  useDeleteProvider,
  useDiscoverModels,
  useProviders,
  useTestProvider,
  useUpdateProvider,
} from "@/lib/hooks";
import type { Provider, ProviderCreate, ProviderStatus } from "@/lib/types";

function statusVariant(status: ProviderStatus) {
  switch (status) {
    case "healthy":
      return "success" as const;
    case "offline":
      return "destructive" as const;
    case "degraded":
      return "warning" as const;
    default:
      return "secondary" as const;
  }
}

export default function ProvidersPage() {
  const providersQuery = useProviders();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Provider | null>(null);
  const [testResult, setTestResult] = useState<{ id: string; message: string; success: boolean } | null>(null);
  const [discoverFor, setDiscoverFor] = useState<Provider | null>(null);
  const [discovered, setDiscovered] = useState<{ id: string; name: string; status: string }[]>([]);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverError, setDiscoverError] = useState("");

  const createProvider = useCreateProvider();
  const updateProvider = useUpdateProvider();
  const deleteProvider = useDeleteProvider();
  const testProvider = useTestProvider();
  const discoverModels = useDiscoverModels(discoverFor?.id ?? null);

  const providers = providersQuery.data ?? [];

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (p: Provider) => {
    setEditing(p);
    setDialogOpen(true);
  };

  const handleSubmit = async (payload: ProviderCreate) => {
    if (editing) {
      await updateProvider.mutateAsync({ id: editing.id, body: payload });
    } else {
      await createProvider.mutateAsync(payload);
    }
  };

  const handleTest = async (p: Provider) => {
    const res = await testProvider.mutateAsync(p.id);
    setTestResult({ id: p.id, message: res.message, success: res.success });
  };

  const handleToggle = async (p: Provider) => {
    await updateProvider.mutateAsync({
      id: p.id,
      body: { name: p.name, type: p.type, base_url: p.base_url, is_enabled: !p.is_enabled },
    });
  };

  const handleDelete = async (p: Provider) => {
    if (!confirm(`Delete provider "${p.name}"?`)) return;
    await deleteProvider.mutateAsync(p.id);
  };

  const handleDiscover = async () => {
    if (!discoverFor) return;
    setDiscoverLoading(true);
    setDiscoverError("");
    setDiscovered([]);
    try {
      const result = await discoverModels.mutateAsync();
      setDiscovered(result);
    } catch (err) {
      setDiscoverError(err instanceof Error ? err.message : "Discovery failed");
    } finally {
      setDiscoverLoading(false);
    }
  };

  const handleClose = (open: boolean) => {
    setDialogOpen(open);
    if (!open) setEditing(null);
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Providers</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Connect and manage AI providers
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> Add Provider
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configured Providers</CardTitle>
        </CardHeader>
        <CardContent>
          {providersQuery.isLoading ? (
            <p className="py-8 text-center text-[var(--muted-foreground)]">Loading…</p>
          ) : providers.length === 0 ? (
            <div className="py-12 text-center">
              <Boxes className="mx-auto h-8 w-8 text-[var(--muted-foreground)]" />
              <p className="mt-3 text-[var(--muted-foreground)]">
                No providers configured yet.
              </p>
              <Button className="mt-4" onClick={openCreate}>
                <Plus className="h-4 w-4" /> Add your first provider
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Base URL</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {providers.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{p.type}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[240px] truncate text-[var(--muted-foreground)]">
                      {p.base_url ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(p.status)}>{p.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          title="Test connection"
                          disabled={testProvider.isPending}
                          onClick={() => handleTest(p)}
                        >
                          <Zap className="h-4 w-4" />
                          Test
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          title="Edit"
                          onClick={() => openEdit(p)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          title={p.is_enabled ? "Disable" : "Enable"}
                          onClick={() => handleToggle(p)}
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          title="Discover models"
                          onClick={() => setDiscoverFor(p)}
                        >
                          <Boxes className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          title="Delete"
                          className="text-red-600 hover:bg-red-50"
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

      <ProviderDialog
        open={dialogOpen}
        onOpenChange={handleClose}
        provider={editing}
        onSubmit={handleSubmit}
      />

      {/* Test result dialog */}
      <Dialog open={Boolean(testResult)} onOpenChange={(o) => !o && setTestResult(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connection Test</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <p className={testResult?.success ? "text-green-600" : "text-red-600"}>
              {testResult?.message}
            </p>
            {testResult?.success && (
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                The provider responded successfully.
              </p>
            )}
          </DialogBody>
        </DialogContent>
      </Dialog>

      {/* Discover models dialog */}
      <Dialog open={Boolean(discoverFor)} onOpenChange={(o) => !o && setDiscoverFor(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Discover Models</DialogTitle>
            <DialogDescription>
              {discoverFor?.name} — fetch available models from this provider.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            {discoverLoading ? (
              <p className="py-4 text-[var(--muted-foreground)]">Discovering…</p>
            ) : discoverError ? (
              <p className="text-sm text-red-600">{discoverError}</p>
            ) : discovered.length === 0 && !discoverLoading ? (
              <p className="py-4 text-[var(--muted-foreground)]">
                No models discovered yet. Run discovery to sync models.
              </p>
            ) : (
              <ul className="space-y-1 text-sm">
                {discovered.map((m) => (
                  <li key={m.id} className="flex items-center justify-between">
                    <span>{m.name}</span>
                    <Badge variant={m.status === "added" ? "success" : "secondary"}>
                      {m.status}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4 flex justify-end">
              <Button onClick={handleDiscover} disabled={discoverLoading}>
                {discoverLoading ? "Discovering…" : "Run discovery"}
              </Button>
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  );
}
