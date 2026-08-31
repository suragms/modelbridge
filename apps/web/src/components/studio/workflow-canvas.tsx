"use client";

import { useCallback, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const NODE_PALETTE = [
  "trigger",
  "ai_model",
  "agent",
  "condition",
  "transform",
  "integration",
  "webhook",
  "approval",
  "output",
] as const;

type StudioNode = {
  id: string;
  type: string;
  config: Record<string, unknown>;
  label?: string;
};

type StudioEdge = {
  source: string;
  target: string;
  sourceHandle?: string;
};

type VisualDefinition = {
  nodes: StudioNode[];
  edges: StudioEdge[];
};

type WorkflowCanvasProps = {
  initial?: VisualDefinition;
  onSave?: (visual: VisualDefinition) => void;
  readOnly?: boolean;
};

function newNode(type: string, index: number): StudioNode {
  const id = `${type}-${index}-${Date.now().toString(36)}`;
  const config: Record<string, unknown> = {};
  if (type === "ai_model") config.model = "auto";
  if (type === "agent") config.agent_id = "";
  if (type === "condition") config.field = "status";
  return { id, type, config, label: type.replace("_", " ") };
}

export function WorkflowCanvas({ initial, onSave, readOnly }: WorkflowCanvasProps) {
  const [visual, setVisual] = useState<VisualDefinition>(
    initial ?? { nodes: [], edges: [] }
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [edgeSource, setEdgeSource] = useState("");
  const [edgeTarget, setEdgeTarget] = useState("");

  const selected = visual.nodes.find((n) => n.id === selectedId);

  const addNode = useCallback((type: string) => {
    setVisual((prev) => ({
      ...prev,
      nodes: [...prev.nodes, newNode(type, prev.nodes.length + 1)],
    }));
  }, []);

  const removeNode = useCallback((id: string) => {
    setVisual((prev) => ({
      nodes: prev.nodes.filter((n) => n.id !== id),
      edges: prev.edges.filter((e) => e.source !== id && e.target !== id),
    }));
    setSelectedId(null);
  }, []);

  const updateConfig = useCallback((key: string, value: string) => {
    if (!selectedId) return;
    setVisual((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) =>
        n.id === selectedId ? { ...n, config: { ...n.config, [key]: value } } : n
      ),
    }));
  }, [selectedId]);

  const addEdge = useCallback(() => {
    if (!edgeSource || !edgeTarget || edgeSource === edgeTarget) return;
    setVisual((prev) => ({
      ...prev,
      edges: [...prev.edges, { source: edgeSource, target: edgeTarget, sourceHandle: "default" }],
    }));
    setEdgeSource("");
    setEdgeTarget("");
  }, [edgeSource, edgeTarget]);

  return (
    <div className="grid gap-4 lg:grid-cols-[220px_1fr_280px]">
      {!readOnly && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Node Palette</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {NODE_PALETTE.map((type) => (
              <Button
                key={type}
                variant="outline"
                size="sm"
                className="w-full justify-start capitalize"
                onClick={() => addNode(type)}
              >
                {type.replace("_", " ")}
              </Button>
            ))}
          </CardContent>
        </Card>
      )}

      <Card className="min-h-[420px]">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Canvas</CardTitle>
          {!readOnly && onSave && (
            <Button size="sm" onClick={() => onSave(visual)}>
              Save Draft
            </Button>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          {visual.nodes.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">
              Add nodes from the palette to build your workflow.
            </p>
          )}
          <div className="grid gap-2 sm:grid-cols-2">
            {visual.nodes.map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => setSelectedId(node.id)}
                className={`rounded border px-3 py-2 text-left text-sm transition-colors ${
                  selectedId === node.id ? "border-[var(--primary)] bg-[var(--muted)]" : ""
                }`}
              >
                <div className="font-medium capitalize">{node.type.replace("_", " ")}</div>
                <div className="text-xs text-[var(--muted-foreground)]">{node.id}</div>
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-1">
            <p className="text-xs font-medium text-[var(--muted-foreground)]">Connections</p>
            {visual.edges.length === 0 && (
              <p className="text-xs text-[var(--muted-foreground)]">No connections yet.</p>
            )}
            {visual.edges.map((edge, i) => (
              <div key={`${edge.source}-${edge.target}-${i}`} className="text-xs">
                {edge.source} → {edge.target}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {!selected && (
            <p className="text-sm text-[var(--muted-foreground)]">Select a node to configure.</p>
          )}
          {selected && (
            <>
              <p className="text-sm font-medium capitalize">{selected.type.replace("_", " ")}</p>
              {selected.type === "ai_model" && (
                <label className="block text-xs">
                  Model
                  <input
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                    value={String(selected.config.model ?? "")}
                    disabled={readOnly}
                    onChange={(e) => updateConfig("model", e.target.value)}
                  />
                </label>
              )}
              {selected.type === "agent" && (
                <label className="block text-xs">
                  Agent ID
                  <input
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                    value={String(selected.config.agent_id ?? "")}
                    disabled={readOnly}
                    onChange={(e) => updateConfig("agent_id", e.target.value)}
                  />
                </label>
              )}
              {selected.type === "condition" && (
                <label className="block text-xs">
                  Field
                  <input
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                    value={String(selected.config.field ?? "")}
                    disabled={readOnly}
                    onChange={(e) => updateConfig("field", e.target.value)}
                  />
                </label>
              )}
              {!readOnly && (
                <Button variant="destructive" size="sm" onClick={() => removeNode(selected.id)}>
                  Remove Node
                </Button>
              )}
            </>
          )}

          {!readOnly && visual.nodes.length >= 2 && (
            <div className="space-y-2 border-t pt-3">
              <p className="text-xs font-medium">Add Connection</p>
              <select
                className="w-full rounded border px-2 py-1 text-sm"
                value={edgeSource}
                onChange={(e) => setEdgeSource(e.target.value)}
              >
                <option value="">Source</option>
                {visual.nodes.map((n) => (
                  <option key={n.id} value={n.id}>{n.id}</option>
                ))}
              </select>
              <select
                className="w-full rounded border px-2 py-1 text-sm"
                value={edgeTarget}
                onChange={(e) => setEdgeTarget(e.target.value)}
              >
                <option value="">Target</option>
                {visual.nodes.map((n) => (
                  <option key={n.id} value={n.id}>{n.id}</option>
                ))}
              </select>
              <Button size="sm" variant="outline" onClick={addEdge}>
                Connect
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export type { VisualDefinition };
