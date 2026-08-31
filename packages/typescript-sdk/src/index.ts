export class ModelBridgeError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string
  ) {
    super(message);
    this.name = "ModelBridgeError";
  }
}

export interface ModelBridgeOptions {
  baseURL?: string;
  apiKey?: string;
  token?: string;
  timeout?: number;
  orgId?: string;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
  tools?: Record<string, unknown>[];
}

export interface EmbeddingRequest {
  model: string;
  input: string | string[];
}

async function parseResponse(res: Response): Promise<unknown> {
  if (res.status === 401) {
    throw new ModelBridgeError("Unauthorized", 401);
  }
  if (!res.ok) {
    const text = await res.text();
    throw new ModelBridgeError(text || res.statusText, res.status);
  }
  if (res.status === 204) return null;
  return res.json();
}

function headers(opts: ModelBridgeOptions, useToken = false): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (useToken && opts.token) {
    h["Authorization"] = `Bearer ${opts.token}`;
  } else if (opts.apiKey) {
    h["Authorization"] = `Bearer ${opts.apiKey}`;
  } else if (opts.token) {
    h["Authorization"] = `Bearer ${opts.token}`;
  }
  if (opts.orgId) {
    h["X-Organization-ID"] = opts.orgId;
  }
  return h;
}

export class ModelBridge {
  private baseURL: string;
  private opts: ModelBridgeOptions;

  constructor(options: ModelBridgeOptions = {}) {
    this.baseURL = (options.baseURL || "http://localhost:8000").replace(/\/$/, "");
    this.opts = { timeout: 120000, ...options };
  }

  chat = {
    completions: {
      create: async (req: ChatCompletionRequest): Promise<unknown> => {
        const res = await fetch(`${this.baseURL}/v1/chat/completions`, {
          method: "POST",
          headers: headers(this.opts),
          body: JSON.stringify({ ...req, stream: false }),
        });
        return parseResponse(res);
      },
      stream: async function* (
        this: ModelBridge,
        req: ChatCompletionRequest
      ): AsyncGenerator<unknown> {
        const res = await fetch(`${this.baseURL}/v1/chat/completions`, {
          method: "POST",
          headers: headers(this.opts),
          body: JSON.stringify({ ...req, stream: true }),
        });
        if (!res.ok) {
          throw new ModelBridgeError(await res.text(), res.status);
        }
        const reader = res.body?.getReader();
        if (!reader) return;
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const payload = line.slice(6).trim();
              if (payload === "[DONE]") return;
              yield JSON.parse(payload);
            }
          }
        }
      }.bind(this),
    },
  };

  embeddings = {
    create: async (req: EmbeddingRequest): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/v1/embeddings`, {
        method: "POST",
        headers: headers(this.opts),
        body: JSON.stringify(req),
      });
      return parseResponse(res);
    },
  };

  async health(): Promise<unknown> {
    const res = await fetch(`${this.baseURL}/health`);
    return parseResponse(res);
  }

  models = {
    list: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/models/`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  analytics = {
    overview: async (params?: Record<string, string>): Promise<unknown> => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      const res = await fetch(`${this.baseURL}/analytics/overview${qs}`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  governance = {
    policies: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/governance/policies`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    events: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/governance/events`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    approvals: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/governance/approvals`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  agents = {
    list: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/agents`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    get: async (agentId: string): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/agents/${agentId}`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    execute: async (
      agentId: string,
      body: { input_text?: string; sync?: boolean } = {}
    ): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/agents/${agentId}/execute`, {
        method: "POST",
        headers: headers(this.opts, true),
        body: JSON.stringify(body),
      });
      return parseResponse(res);
    },
    getExecution: async (executionId: string): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/agents/executions/${executionId}`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  workflows = {
    list: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/workflows`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    execute: async (
      workflowId: string,
      body: { sync?: boolean; context?: Record<string, unknown> } = {}
    ): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/workflows/${workflowId}/execute`, {
        method: "POST",
        headers: headers(this.opts, true),
        body: JSON.stringify(body),
      });
      return parseResponse(res);
    },
    getExecution: async (executionId: string): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/workflows/executions/${executionId}`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  extensions = {
    packages: async (params?: Record<string, string>): Promise<unknown> => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      const res = await fetch(`${this.baseURL}/extensions/packages${qs}`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    installations: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/extensions/installations`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  templates = {
    list: async (params?: Record<string, string>): Promise<unknown> => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      const res = await fetch(`${this.baseURL}/templates${qs}`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  enterprise = {
    overview: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/enterprise/overview`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    workspaces: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/workspaces`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    projects: async (params?: Record<string, string>): Promise<unknown> => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      const res = await fetch(`${this.baseURL}/projects${qs}`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    fleet: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/fleet`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  cloud = {
    health: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/cloud/health`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    regions: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/cloud/regions`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    instances: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/cloud/instances`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    instance: async (id: string): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/cloud/instances/${id}`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };

  usage = {
    summary: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/usage/summary`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
    quotas: async (): Promise<unknown> => {
      const res = await fetch(`${this.baseURL}/quotas`, {
        headers: headers(this.opts, true),
      });
      return parseResponse(res);
    },
  };
}
