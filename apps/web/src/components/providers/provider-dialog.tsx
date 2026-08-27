"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
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
import type { Provider, ProviderCreate, ProviderType } from "@/lib/types";

interface ProviderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider?: Provider | null; // when set, edits; otherwise creates
  onSubmit: (payload: ProviderCreate) => Promise<void>;
}

const TYPE_LABELS: { value: ProviderType; label: string; defaultUrl: string }[] = [
  { value: "ollama", label: "Ollama", defaultUrl: "http://localhost:11434" },
  { value: "openai", label: "OpenAI", defaultUrl: "https://api.openai.com/v1" },
  { value: "anthropic", label: "Anthropic", defaultUrl: "https://api.anthropic.com" },
  { value: "gemini", label: "Gemini", defaultUrl: "https://generativelanguage.googleapis.com" },
  { value: "groq", label: "Groq", defaultUrl: "https://api.groq.com/openai/v1" },
  { value: "openrouter", label: "OpenRouter", defaultUrl: "https://openrouter.ai/api/v1" },
  { value: "lmstudio", label: "LM Studio", defaultUrl: "http://localhost:1234/v1" },
  { value: "custom", label: "Custom", defaultUrl: "" },
];

export function ProviderDialog({
  open,
  onOpenChange,
  provider,
  onSubmit,
}: ProviderDialogProps) {
  const [name, setName] = useState("");
  const [type, setType] = useState<ProviderType>("ollama");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setName(provider?.name ?? "");
      setType((provider?.type as ProviderType) ?? "ollama");
      setBaseUrl(provider?.base_url ?? "");
      setApiKey("");
      setError("");
    }
  }, [open, provider]);

  const changeType = (t: ProviderType) => {
    setType(t);
    const preset = TYPE_LABELS.find((l) => l.value === t)?.defaultUrl ?? "";
    if (!baseUrl || !provider) setBaseUrl(preset);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({
        name,
        type,
        base_url: type === "ollama" || baseUrl ? baseUrl : null,
        api_key: apiKey || null,
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save provider");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{provider ? "Edit Provider" : "Add Provider"}</DialogTitle>
            <DialogDescription>
              {provider
                ? `Update ${provider.name}`
                : "Connect an AI provider to ModelBridge."}
            </DialogDescription>
          </DialogHeader>

          <DialogBody className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="p-name">Provider Name</Label>
              <Input
                id="p-name"
                placeholder="My Ollama"
                value={name}
                required
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            {!provider && (
              <div className="space-y-2">
                <Label htmlFor="p-type">Type</Label>
                <Select
                  id="p-type"
                  value={type}
                  onChange={(e) => changeType(e.target.value as ProviderType)}
                >
                  {TYPE_LABELS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="p-url">Base URL</Label>
              <Input
                id="p-url"
                placeholder="http://localhost:11434"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
              />
              <p className="text-xs text-[var(--muted-foreground)]">
                Default for Ollama: http://localhost:11434
              </p>
            </div>

            {type !== "ollama" && (
              <div className="space-y-2">
                <Label htmlFor="p-key">API Key</Label>
                <Input
                  id="p-key"
                  type="password"
                  placeholder="Optional"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <p className="text-xs text-[var(--muted-foreground)]">
                  Encrypted before it is stored.
                </p>
              </div>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}
          </DialogBody>

          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving…" : provider ? "Save changes" : "Add provider"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
