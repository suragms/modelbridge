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
  max_output_tokens?: number | null;
  embedding_dimensions?: number | null;
  supports_chat?: boolean;
  supports_streaming: boolean;
  supports_tools: boolean;
  supports_tool_choice?: boolean;
  supports_embeddings: boolean;
  supports_vision: boolean;
  supports_json_mode: boolean;
  supports_structured_output?: boolean;
  supports_reasoning?: boolean;
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
  status: "COMPLETED" | "FAILED" | "success" | "error" | string;
  error?: string | null;
  routing_strategy?: string | null;
  fallback_used: boolean;
  requested_model?: string | null;
  selected_model?: string | null;
  routing_policy?: string | null;
  candidates_count?: number | null;
  fallback_count?: number | null;
  created_at: string;
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
  usage_source?: string | null;
  estimated_total_cost?: number | null;
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
  has_data?: boolean;
}

export interface AnalyticsOverview extends AnalyticsSummary {
  has_data: boolean;
  message?: string;
  successful_requests?: number;
  failed_requests?: number;
  total_input_tokens?: number;
  total_output_tokens?: number;
  active_providers?: number;
  active_models?: number;
  cost_disclaimer?: string;
}

export interface AnalyticsTimeSeries {
  bucket: string;
  metric: string;
  data: Array<{ timestamp: string; value: number }>;
  cost_disclaimer?: string;
}

export interface AnalyticsProviders {
  breakdown: Array<{
    provider: string;
    total_requests: number;
    success_rate: number;
    average_latency_ms: number;
    total_tokens: number;
    estimated_cost: number;
    error_count: number;
  }>;
  performance: Array<Record<string, unknown>>;
}

export interface AnalyticsError {
  request_id: string;
  error_type: string;
  error_code: string | null;
  provider: string;
  model: string;
  timestamp: string;
  message: string | null;
}

export interface RequestLogList {
  items: RequestLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface RequestDetail extends RequestLog {
  estimated_input_cost?: number | null;
  estimated_output_cost?: number | null;
  cost_is_estimated?: boolean | null;
  pricing_source?: string | null;
  currency?: string | null;
  cost_disclaimer?: string;
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
  usage_source?: string | null;
  selected_model?: string | null;
  provider_latency_ms?: number | null;
  completed_at?: string | null;
  error_code?: string | null;
  error_type?: string | null;
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
  eligible?: boolean;
  filter_reason?: string | null;
}

export interface RoutingDebugEntry {
  model_id: string;
  model_name: string;
  provider_name: string;
  eligible: boolean;
  filter_reason?: string | null;
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
  debug?: RoutingDebugEntry[];
  requested_capabilities?: string[];
  selected: RouteCandidate | null;
  strategy: string;
  reason: string;
  fallback_order: string[];
}

// Playground types
export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  name?: string | null;
  tool_call_id?: string | null;
  tool_calls?: Array<Record<string, unknown>> | null;
}

export interface PlaygroundChatRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number | null;
  top_p?: number | null;
  max_tokens?: number | null;
  stream?: boolean;
  stop?: string | string[] | null;
  tools?: Array<Record<string, unknown>> | null;
  tool_choice?: string | Record<string, unknown> | null;
  response_format?: Record<string, unknown> | null;
}

export interface PlaygroundRoutingInfo {
  requested_model: string;
  selected_model: string;
  provider: string;
  strategy: string;
  routing_policy?: string | null;
  required_capabilities: string[];
}

export interface PlaygroundChatResponse {
  request_id: string;
  response: {
    id: string;
    object: string;
    created: number;
    model: string;
    choices: Array<{
      index: number;
      message: {
        role: string;
        content: string | null;
        tool_calls?: Array<Record<string, unknown>> | null;
      };
      finish_reason: string | null;
    }>;
    usage?: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    };
  };
  routing: PlaygroundRoutingInfo;
  latency_ms: number;
  estimated_total_cost?: number | null;
  usage_source?: string | null;
}

export interface PlaygroundCompareSide {
  model: string;
  provider?: string | null;
  request_id?: string | null;
  success: boolean;
  response?: PlaygroundChatResponse["response"] | null;
  error?: string | null;
  latency_ms?: number | null;
  total_tokens?: number | null;
  estimated_total_cost?: number | null;
}

export interface PlaygroundCompareRequest {
  model_a: string;
  model_b: string;
  messages: ChatMessage[];
  temperature?: number | null;
  max_tokens?: number | null;
  tools?: Array<Record<string, unknown>> | null;
  tool_choice?: string | Record<string, unknown> | null;
  response_format?: Record<string, unknown> | null;
}

export interface PlaygroundCompareResponse {
  side_a: PlaygroundCompareSide;
  side_b: PlaygroundCompareSide;
}
