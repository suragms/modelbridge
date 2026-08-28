"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "./api";
import { useAuth } from "./auth";
import type {
  APIKey,
  APIKeyCreated,
  AIModel,
  AnalyticsSummary,
  AnalyticsOverview,
  AnalyticsTimeSeries,
  AnalyticsProviders,
  AnalyticsError,
  DiscoveredModel,
  HealthStatus,
  Provider,
  ProviderCreate,
  ProviderTestResult,
  ProviderUpdate,
  RequestLog,
  RequestLogList,
  RequestDetail,
  RoutingPolicy,
  RoutingPolicyCreate,
  RoutingPolicyUpdate,
  RoutingTestRequest,
  RoutingTestResponse,
  PlaygroundChatRequest,
  PlaygroundChatResponse,
  PlaygroundCompareRequest,
  PlaygroundCompareResponse,
} from "./types";

function useToken(): string | null {
  const { token } = useAuth();
  return token;
}

function useOrgId(): string | null {
  const { activeOrgId, user } = useAuth();
  return activeOrgId ?? user?.organization_id ?? null;
}

// ---- Providers -------------------------------------------------------------

export function useProviders() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery<Provider[]>({
    queryKey: ["providers", orgId],
    queryFn: () => api.get<Provider[]>("/providers", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token),
  });
}

export function useCreateProvider() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProviderCreate) =>
      api.post<Provider>("/providers", payload, token ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["providers"] }),
  });
}

export function useUpdateProvider() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ProviderUpdate }) =>
      api.put<Provider>(`/providers/${id}`, body, token ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["providers"] }),
  });
}

export function useDeleteProvider() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/providers/${id}`, token ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["providers"] }),
  });
}

export function useTestProvider() {
  const token = useToken();
  return useMutation({
    mutationFn: (id: string) =>
      api.post<ProviderTestResult>(`/providers/${id}/test`, undefined, token ?? undefined),
  });
}

export function useDiscoverModels(providerId: string | null) {
  const token = useToken();
  return useMutation({
    mutationFn: () =>
      api.post<DiscoveredModel[]>(
        `/providers/${providerId}/discover-models`,
        undefined,
        token ?? undefined
      ),
  });
}

// ---- Models ----------------------------------------------------------------

export function useModels() {
  const token = useToken();
  return useQuery<AIModel[]>({
    queryKey: ["models"],
    queryFn: () => api.get<AIModel[]>("/models", token ?? undefined),
    enabled: Boolean(token),
  });
}

// ---- API Keys --------------------------------------------------------------

export function useApiKeys() {
  const token = useToken();
  return useQuery<APIKey[]>({
    queryKey: ["api-keys"],
    queryFn: () => api.get<APIKey[]>("/api-keys", token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useCreateApiKey() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; expires_in_days?: number | null }) =>
      api.post<APIKeyCreated>("/api-keys", payload, token ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

export function useRevokeApiKey() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/api-keys/${id}`, token ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

// ---- Routing policies -------------------------------------------------------

export function useRoutingPolicies() {
  const token = useToken();
  return useQuery<RoutingPolicy[]>({
    queryKey: ["routing-policies"],
    queryFn: () => api.get<RoutingPolicy[]>("/routing/policies", token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useCreateRoutingPolicy() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: RoutingPolicyCreate) =>
      api.post<RoutingPolicy>("/routing/policies", payload, token ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["routing-policies"] }),
  });
}

export function useUpdateRoutingPolicy() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: RoutingPolicyUpdate }) =>
      api.patch<RoutingPolicy>(`/routing/policies/${id}`, body, token ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["routing-policies"] }),
  });
}

export function useDeleteRoutingPolicy() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/routing/policies/${id}`, token ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["routing-policies"] }),
  });
}

export function useTestRouting() {
  const token = useToken();
  return useMutation({
    mutationFn: (payload: RoutingTestRequest) =>
      api.post<RoutingTestResponse>("/routing/test", payload, token ?? undefined),
  });
}

// ---- Playground --------------------------------------------------------------

export function usePlaygroundChat() {
  const token = useToken();
  return useMutation({
    mutationFn: (payload: PlaygroundChatRequest) =>
      api.post<PlaygroundChatResponse>("/playground/chat", payload, token ?? undefined),
  });
}

export function usePlaygroundCompare() {
  const token = useToken();
  return useMutation({
    mutationFn: (payload: PlaygroundCompareRequest) =>
      api.post<PlaygroundCompareResponse>("/playground/compare", payload, token ?? undefined),
  });
}

// ---- Model sync -------------------------------------------------------------

export function useSyncModels() {
  const token = useToken();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (providerId: string) =>
      api.post<DiscoveredModel[]>(
        `/providers/${providerId}/models/sync`,
        undefined,
        token ?? undefined
      ),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["models"] });
      client.invalidateQueries({ queryKey: ["providers"] });
    },
  });
}

// ---- Requests / logs -------------------------------------------------------

function buildQuery(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

export function useRequestLogs(filters?: {
  limit?: number;
  offset?: number;
  status?: string;
  provider?: string;
  model?: string;
  request_id?: string;
}) {
  const token = useToken();
  const query = buildQuery({
    limit: filters?.limit ?? 50,
    offset: filters?.offset ?? 0,
    status: filters?.status,
    provider: filters?.provider,
    model: filters?.model,
    request_id: filters?.request_id,
  });
  return useQuery<RequestLogList>({
    queryKey: ["request-logs", filters],
    queryFn: () => api.get<RequestLogList>(`/logs${query}`, token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useRequestDetail(requestId: string) {
  const token = useToken();
  return useQuery<RequestDetail>({
    queryKey: ["request-detail", requestId],
    queryFn: () => api.get<RequestDetail>(`/logs/${requestId}`, token ?? undefined),
    enabled: Boolean(token) && Boolean(requestId),
  });
}

// ---- Health / analytics ----------------------------------------------------

export function useHealth() {
  return useQuery<HealthStatus>({
    queryKey: ["health"],
    queryFn: () => api.get<HealthStatus>("/health"),
    refetchInterval: 15000,
  });
}

export function useAnalyticsSummary() {
  const token = useToken();
  return useQuery<AnalyticsSummary>({
    queryKey: ["analytics-summary"],
    queryFn: () => api.get<AnalyticsSummary>("/analytics/summary", token ?? undefined),
    enabled: Boolean(token),
  });
}

function useDateParams(dates?: { start?: string; end?: string }) {
  return buildQuery({ start_date: dates?.start, end_date: dates?.end });
}

export function useAnalyticsOverview(dates?: { start?: string; end?: string }) {
  const token = useToken();
  const q = useDateParams(dates);
  return useQuery<AnalyticsOverview>({
    queryKey: ["analytics-overview", dates],
    queryFn: () => api.get<AnalyticsOverview>(`/analytics/overview${q}`, token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useAnalyticsRequests(dates?: { start?: string; end?: string }) {
  const token = useToken();
  const q = useDateParams(dates);
  return useQuery<AnalyticsTimeSeries>({
    queryKey: ["analytics-requests", dates],
    queryFn: () => api.get<AnalyticsTimeSeries>(`/analytics/requests${q}`, token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useAnalyticsTokens(dates?: { start?: string; end?: string }) {
  const token = useToken();
  const q = useDateParams(dates);
  return useQuery<AnalyticsTimeSeries>({
    queryKey: ["analytics-tokens", dates],
    queryFn: () => api.get<AnalyticsTimeSeries>(`/analytics/tokens${q}`, token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useAnalyticsCost(dates?: { start?: string; end?: string }) {
  const token = useToken();
  const q = useDateParams(dates);
  return useQuery<AnalyticsTimeSeries>({
    queryKey: ["analytics-cost", dates],
    queryFn: () => api.get<AnalyticsTimeSeries>(`/analytics/cost${q}`, token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useAnalyticsLatency(dates?: { start?: string; end?: string }) {
  const token = useToken();
  const q = useDateParams(dates);
  return useQuery<AnalyticsTimeSeries>({
    queryKey: ["analytics-latency", dates],
    queryFn: () => api.get<AnalyticsTimeSeries>(`/analytics/latency${q}`, token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useAnalyticsProviders(dates?: { start?: string; end?: string }) {
  const token = useToken();
  const q = useDateParams(dates);
  return useQuery<AnalyticsProviders>({
    queryKey: ["analytics-providers", dates],
    queryFn: () => api.get<AnalyticsProviders>(`/analytics/providers${q}`, token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useAnalyticsModels(dates?: { start?: string; end?: string }) {
  const token = useToken();
  const q = useDateParams(dates);
  return useQuery<Array<Record<string, unknown>>>({
    queryKey: ["analytics-models", dates],
    queryFn: () => api.get<Array<Record<string, unknown>>>(`/analytics/models${q}`, token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useAnalyticsErrors(dates?: { start?: string; end?: string }) {
  const token = useToken();
  const q = useDateParams(dates);
  return useQuery<{ errors: AnalyticsError[]; time_series: AnalyticsTimeSeries }>({
    queryKey: ["analytics-errors", dates],
    queryFn: () =>
      api.get<{ errors: AnalyticsError[]; time_series: AnalyticsTimeSeries }>(
        `/analytics/errors${q}`,
        token ?? undefined
      ),
    enabled: Boolean(token),
  });
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

// ---- Organizations ---------------------------------------------------------

export function useOrganizations() {
  const token = useToken();
  return useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.get<Array<Record<string, unknown>>>("/organizations/", token ?? undefined),
    enabled: Boolean(token),
  });
}

export function useOrganizationSettings() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["org-settings", orgId],
    queryFn: () =>
      api.get<Record<string, unknown>>(
        "/organizations/current/settings",
        token ?? undefined,
        orgId ?? undefined
      ),
    enabled: Boolean(token && orgId),
  });
}

export function useOrganizationMembers() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["org-members", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>(
        "/organizations/current/members",
        token ?? undefined,
        orgId ?? undefined
      ),
    enabled: Boolean(token && orgId),
  });
}

export function useUpdateOrganizationSettings() {
  const token = useToken();
  const orgId = useOrgId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.patch("/organizations/current/settings", body, token ?? undefined, orgId ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["org-settings"] }),
  });
}

export function useBudgetAlerts() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["budget-alerts", orgId],
    queryFn: () =>
      api.get<{ alerts?: unknown[] } | unknown[]>(
        "/organizations/current/budget-alerts",
        token ?? undefined,
        orgId ?? undefined
      ),
    enabled: Boolean(token && orgId),
  });
}
