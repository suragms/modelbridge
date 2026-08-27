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
  has_api_key: boolean;
  last_health_check_at: string | null;
  last_health_latency_ms: number | null;
  total_health_checks: number;
  failed_health_checks: number;
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
  status: "added" | "exists" | "updated" | "unavailable" | string;
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
  quality_score: number;
  input_price_per_1k: number;
  output_price_per_1k: number;
  average_latency_ms: number | null;
  last_synced_at: string | null;
  updated_at: string | null;
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
  routing_strategy?: string | null;
  fallback_used: boolean;
  requested_model?: string | null;
  routing_policy?: string | null;
  candidates_count?: number | null;
  fallback_count?: number | null;
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

// Routing types
export type RoutingStrategy =
  | "auto"
  | "balanced"
  | "priority"
  | "cheapest"
  | "fastest"
  | "quality"
  | "local_only"
  | "privacy_first"
  | "round_robin"
  | "least_latency";

export interface RoutingPolicy {
  id: string;
  name: string;
  description: string | null;
  strategy: RoutingStrategy;
  is_default: boolean;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
}

export interface RoutingPolicyCreate {
  name: string;
  description?: string | null;
  strategy: RoutingStrategy;
  config?: Record<string, unknown> | null;
  is_default?: boolean;
}

export interface RoutingPolicyUpdate {
  name?: string;
  description?: string | null;
  strategy?: RoutingStrategy;
  config?: Record<string, unknown> | null;
  is_default?: boolean;
}

export interface RouteCandidate {
  model_id: string;
  model_name: string;
  provider_name: string;
  provider_type: string;
  score: number;
  latency_ms: number;
  cost_per_1k: number;
  is_local: boolean;
}

export interface RoutingTestRequest {
  requested_model: string;
  required_capabilities?: string[];
  strategy?: RoutingStrategy;
  policy_name?: string;
}

export interface RoutingTestResponse {
  candidates: RouteCandidate[];
  filtered: RouteCandidate[];
  selected: RouteCandidate | null;
  strategy: string;
  reason: string;
  fallback_order: string[];
}
