// Types mirroring the ModelBridge backend API schemas.

export type ProviderType =
  | "ollama"
  | "openai"
  | "anthropic"
  | "gemini"
  | "groq"
  | "openrouter"
  | "lmstudio"
  | "custom";

export type ProviderStatus = "healthy" | "degraded" | "offline" | "unknown";

export interface Provider {
  id: string;
  name: string;
  type: ProviderType;
  base_url: string | null;
  status: ProviderStatus;
  is_enabled: boolean;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ProviderCreate {
  name: string;
  type: ProviderType;
  base_url?: string | null;
  api_key?: string | null;
  config?: Record<string, unknown> | null;
}

export interface ProviderUpdate {
  name?: string;
  type?: ProviderType;
  base_url?: string | null;
  api_key?: string | null;
  is_enabled?: boolean;
  config?: Record<string, unknown> | null;
}

export interface ProviderTestResult {
  success: boolean;
  message: string;
  latency_ms: number | null;
  models_found: string[];
}

export interface DiscoveredModel {
  id: string;
  name: string;
  status: "added" | "exists" | string;
}

export interface AIModel {
  id: string;
  provider_model_id: string;
  display_name: string;
  provider_id: string;
  provider_name?: string;
  context_window: number;
  supports_streaming: boolean;
  supports_tools: boolean;
  supports_embeddings: boolean;
  supports_vision: boolean;
  supports_json_mode: boolean;
  is_enabled: boolean;
  status?: string;
  created_at: string;
}

export interface APIKey {
  id: string;
  key_prefix: string;
  name: string;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
}

export interface APIKeyCreated extends APIKey {
  key: string; // only ever returned once, at creation
}

export interface RequestLog {
  id?: string;
  request_id: string;
  model: string;
  provider: string;
  latency_ms: number;
  status: "success" | "error" | string;
  error?: string | null;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  organization_id: string | null;
  created_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface HealthStatus {
  status: string;
  version?: string;
  checks?: Record<string, string>;
}

export interface DashboardStats {
  activeProviders: number;
  availableModels: number;
  totalRequests: number;
  systemStatus: string;
}

export interface AnalyticsSummary {
  total_requests: number;
  total_tokens: number;
  estimated_total_cost: number;
  success_rate: number;
  average_latency_ms: number;
}
