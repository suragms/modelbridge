"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "./api";
import { useAuth } from "./auth";
import type {
  APIKey,
  APIKeyCreated,
  AIModel,
  AnalyticsSummary,
  DiscoveredModel,
  HealthStatus,
  Provider,
  ProviderCreate,
  ProviderTestResult,
  ProviderUpdate,
  RequestLog,
} from "./types";

function useToken(): string | null {
  const { token } = useAuth();
  return token;
}

// ---- Providers -------------------------------------------------------------

export function useProviders() {
  const token = useToken();
  return useQuery<Provider[]>({
    queryKey: ["providers"],
    queryFn: () => api.get<Provider[]>("/providers", token ?? undefined),
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

// ---- Requests / logs -------------------------------------------------------

export function useRequestLogs() {
  const token = useToken();
  return useQuery<RequestLog[]>({
    queryKey: ["request-logs"],
    queryFn: () => api.get<RequestLog[]>("/logs?limit=50", token ?? undefined),
    enabled: Boolean(token),
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

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
