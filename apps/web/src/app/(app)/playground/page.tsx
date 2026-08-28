"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { FlaskConical, GitCompare, Plus, Send, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useModels, usePlaygroundChat } from "@/lib/hooks";
import type { ChatMessage, PlaygroundChatResponse } from "@/lib/types";

type UiMessage = ChatMessage & { id: string };

function newMessage(role: UiMessage["role"], content: string): UiMessage {
  return { id: crypto.randomUUID(), role, content };
}

function extractAssistantText(result: PlaygroundChatResponse): string {
  const choice = result.response.choices[0];
  if (!choice) return "";
  const msg = choice.message;
  if (msg.content) return msg.content;
  if (msg.tool_calls?.length) {
    return JSON.stringify(msg.tool_calls, null, 2);
  }
  return "";
}

export default function PlaygroundPage() {
  const modelsQuery = useModels();
  const chatMutation = usePlaygroundChat();

  const [model, setModel] = useState("auto");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [messages, setMessages] = useState<UiMessage[]>([
    newMessage("user", "Explain what ModelBridge does in one sentence."),
  ]);
  const [temperature, setTemperature] = useState("0.7");
  const [maxTokens, setMaxTokens] = useState("512");
  const [jsonMode, setJsonMode] = useState(false);
  const [toolsJson, setToolsJson] = useState("");
  const [result, setResult] = useState<PlaygroundChatResponse | null>(null);
  const [error, setError] = useState("");

  const modelOptions = useMemo(() => {
    const models = (modelsQuery.data ?? []).filter((m) => m.is_enabled);
    const chatModels = models.filter(
      (m) => m.supports_chat !== false && !m.supports_embeddings
    );
    return chatModels.length > 0 ? chatModels : models;
  }, [modelsQuery.data]);

  const buildPayloadMessages = (): ChatMessage[] => {
    const out: ChatMessage[] = [];
    if (systemPrompt.trim()) {
      out.push({ role: "system", content: systemPrompt.trim() });
    }
    for (const m of messages) {
      out.push({ role: m.role, content: m.content });
    }
    return out;
  };

  const handleSend = async () => {
    setError("");
    setResult(null);

    let tools: Array<Record<string, unknown>> | undefined;
    if (toolsJson.trim()) {
      try {
        const parsed = JSON.parse(toolsJson);
        tools = Array.isArray(parsed) ? parsed : [parsed];
      } catch {
        setError("Tools must be valid JSON array");
        return;
      }
    }

    try {
      const res = await chatMutation.mutateAsync({
        model,
        messages: buildPayloadMessages(),
        temperature: temperature ? Number(temperature) : undefined,
        max_tokens: maxTokens ? Number(maxTokens) : undefined,
        tools,
        response_format: jsonMode ? { type: "json_object" } : undefined,
        stream: false,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">AI Playground</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Test models through the same gateway routing and observability stack
          </p>
        </div>
        <Link href="/playground/compare">
          <Button variant="outline">
            <GitCompare className="h-4 w-4" /> Compare models
          </Button>
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FlaskConical className="h-4 w-4" /> Request
            </CardTitle>
            <CardDescription>Configure model, parameters, and tools</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="pg-model">Model</Label>
              <Select id="pg-model" value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="auto">auto (router picks best)</option>
                {modelOptions.map((m) => (
                  <option key={m.id} value={m.provider_model_id}>
                    {m.display_name || m.provider_model_id}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="pg-system">System prompt</Label>
              <textarea
                id="pg-system"
                className="min-h-[72px] w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Optional system instructions"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="pg-temp">Temperature</Label>
                <Input
                  id="pg-temp"
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pg-max">Max tokens</Label>
                <Input
                  id="pg-max"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(e.target.value)}
                />
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={jsonMode} onChange={(e) => setJsonMode(e.target.checked)} />
              JSON mode (response_format: json_object)
            </label>

            <div className="space-y-1.5">
              <Label htmlFor="pg-tools">Tools (JSON array, optional)</Label>
              <textarea
                id="pg-tools"
                className="min-h-[96px] w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-xs"
                value={toolsJson}
                onChange={(e) => setToolsJson(e.target.value)}
                placeholder={'[{"type":"function","function":{"name":"get_weather","parameters":{"type":"object","properties":{"location":{"type":"string"}}}}}]'}
              />
            </div>

            <Button className="w-full" onClick={handleSend} disabled={chatMutation.isPending}>
              <Send className="h-4 w-4" />
              {chatMutation.isPending ? "Sending…" : "Send request"}
            </Button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Conversation</CardTitle>
              <CardDescription>Messages sent to the gateway (not persisted)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {messages.map((m, idx) => (
                <div key={m.id} className="rounded-lg border border-[var(--border)] p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <Badge variant="secondary">{m.role}</Badge>
                    {messages.length > 1 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setMessages((prev) => prev.filter((x) => x.id !== m.id))}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                  <textarea
                    className="min-h-[72px] w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
                    value={m.content ?? ""}
                    onChange={(e) =>
                      setMessages((prev) =>
                        prev.map((x, i) => (i === idx ? { ...x, content: e.target.value } : x))
                      )
                    }
                  />
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setMessages((prev) => [...prev, newMessage("user", "")])}
              >
                <Plus className="h-4 w-4" /> Add message
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Response</CardTitle>
            </CardHeader>
            <CardContent>
              {!result ? (
                <p className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                  Run a request to see the assistant response and routing metadata.
                </p>
              ) : (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">Provider: {result.routing.provider}</Badge>
                    <Badge variant="secondary">Model: {result.routing.selected_model}</Badge>
                    <Badge variant="secondary">Strategy: {result.routing.strategy}</Badge>
                    <Badge variant="secondary">{Math.round(result.latency_ms)} ms</Badge>
                    {result.response.usage && (
                      <Badge variant="secondary">
                        {result.response.usage.total_tokens} tokens
                      </Badge>
                    )}
                    {result.estimated_total_cost != null && (
                      <Badge variant="secondary">
                        ~${result.estimated_total_cost.toFixed(6)}
                      </Badge>
                    )}
                  </div>
                  {result.routing.required_capabilities.length > 0 && (
                    <p className="text-xs text-[var(--muted-foreground)]">
                      Required capabilities: {result.routing.required_capabilities.join(", ")}
                    </p>
                  )}
                  <pre className="max-h-[420px] overflow-auto rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 p-4 text-sm whitespace-pre-wrap">
                    {extractAssistantText(result)}
                  </pre>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Request ID: {result.request_id}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
