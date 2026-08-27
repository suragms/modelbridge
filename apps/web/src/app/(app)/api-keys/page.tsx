"use client";

import { useState } from "react";
import { Copy, KeyRound, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "@/lib/hooks";
import type { APIKeyCreated } from "@/lib/types";

export default function ApiKeysPage() {
  const keysQuery = useApiKeys();
  const createKey = useCreateApiKey();
  const revokeKey = useRevokeApiKey();

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [expiresInDays, setExpiresInDays] = useState("30");
  const [created, setCreated] = useState<APIKeyCreated | null>(null);
  const [error, setError] = useState("");

  const keys = keysQuery.data ?? [];

  const openCreate = () => {
    setName("");
    setError("");
    setCreated(null);
    setCreateOpen(true);
  };

  const handleCreate = async () => {
    setError("");
    const expires = expiresInDays ? Number(expiresInDays) : null;
    const result = await createKey.mutateAsync({
      name: name || "My API key",
      expires_in_days: expires && expires > 0 ? expires : null,
    });
    setCreated(result);
  };

  const handleRevoke = async (id: string) => {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    await revokeKey.mutateAsync(id);
  };

  const copyKey = async () => {
    if (created) await navigator.clipboard.writeText(created.key);
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">API Keys</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Keys used to authenticate requests to /v1/chat/completions
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> Create API Key
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your API Keys</CardTitle>
        </CardHeader>
        <CardContent>
          {keysQuery.isLoading ? (
            <p className="py-8 text-center text-[var(--muted-foreground)]">Loading…</p>
          ) : keys.length === 0 ? (
            <div className="py-12 text-center">
              <KeyRound className="mx-auto h-8 w-8 text-[var(--muted-foreground)]" />
              <p className="mt-3 text-[var(--muted-foreground)]">
                No API keys yet. Create one to call the gateway.
              </p>
              <Button className="mt-4" onClick={openCreate}>
                <Plus className="h-4 w-4" /> Create API Key
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((k) => (
                  <TableRow key={k.id}>
                    <TableCell className="font-medium">{k.name}</TableCell>
                    <TableCell className="font-mono text-xs text-[var(--muted-foreground)]">
                      {k.key_prefix}••••••••••••••
                    </TableCell>
                    <TableCell>
                      <Badge variant={k.is_active ? "success" : "secondary"}>
                        {k.is_active ? "Active" : "Revoked"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-[var(--muted-foreground)]">
                      {new Date(k.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-[var(--muted-foreground)]">
                      {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never"}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end">
                        {k.is_active && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:bg-red-50"
                            onClick={() => handleRevoke(k.id)}
                          >
                            <Trash2 className="h-4 w-4" /> Revoke
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              The full key is shown only once after creation.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            {created ? (
              <div className="space-y-4">
                <div className="rounded-md border border-green-600/40 bg-green-50 p-4">
                  <p className="text-sm font-medium text-green-800">
                    Copy this key now. It will not be shown again.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Input readOnly value={created.key} className="font-mono" />
                  <Button variant="secondary" size="icon" onClick={copyKey} title="Copy">
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
                <div className="text-xs text-[var(--muted-foreground)]">
                  <p>
                    Usage: <code>curl http://localhost:8000/v1/chat/completions -H
                    &quot;Authorization: Bearer {created.key}&quot;</code>
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="k-name">Key name</Label>
                  <Input
                    id="k-name"
                    placeholder="Production"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="k-exp">Expires in</Label>
                  <Select
                    id="k-exp"
                    value={expiresInDays}
                    onChange={(e) => setExpiresInDays(e.target.value)}
                  >
                    <option value="30">30 days</option>
                    <option value="90">90 days</option>
                    <option value="365">1 year</option>
                    <option value="">Never expires</option>
                  </Select>
                </div>
                {error && <p className="text-sm text-red-600">{error}</p>}
              </div>
            )}
          </DialogBody>
          <DialogFooter>
            {created ? (
              <Button onClick={() => setCreateOpen(false)}>Done</Button>
            ) : (
              <>
                <Button variant="secondary" onClick={() => setCreateOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCreate} disabled={createKey.isPending}>
                  {createKey.isPending ? "Creating…" : "Create key"}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
