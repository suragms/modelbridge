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

export function useGovernanceOverview() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["governance-overview", orgId],
    queryFn: () =>
      api.get<Record<string, unknown>>("/governance/overview", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useGovernancePolicies() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["governance-policies", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>("/governance/policies", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useGovernancePolicy(id: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["governance-policy", orgId, id],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/governance/policies/${id}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId && id),
  });
}

export function useCreateGovernancePolicy() {
  const token = useToken();
  const orgId = useOrgId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post("/governance/policies", body, token ?? undefined, orgId ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["governance-policies"] }),
  });
}

export function useUpdateGovernancePolicy() {
  const token = useToken();
  const orgId = useOrgId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.patch(`/governance/policies/${id}`, body, token ?? undefined, orgId ?? undefined),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["governance-policies"] });
      client.invalidateQueries({ queryKey: ["governance-policy"] });
    },
  });
}

export function useDeleteGovernancePolicy() {
  const token = useToken();
  const orgId = useOrgId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`/governance/policies/${id}`, token ?? undefined, orgId ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["governance-policies"] }),
  });
}

export function useSimulatePolicy() {
  const token = useToken();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<Record<string, unknown>>("/governance/simulate", body, token ?? undefined, orgId ?? undefined),
  });
}

export function useGovernanceEvents() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["governance-events", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>("/governance/events", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useGovernanceApprovals() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["governance-approvals", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>("/governance/approvals", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useReviewApproval() {
  const token = useToken();
  const orgId = useOrgId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, comment }: { id: string; action: "approve" | "reject"; comment?: string }) =>
      api.post(`/governance/approvals/${id}/${action}`, { comment }, token ?? undefined, orgId ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["governance-approvals"] }),
  });
}

export function useGovernanceSettings() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["governance-settings", orgId],
    queryFn: () =>
      api.get<Record<string, unknown>>("/governance/settings", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useUpdateGovernanceSettings() {
  const token = useToken();
  const orgId = useOrgId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.patch("/governance/settings", body, token ?? undefined, orgId ?? undefined),
    onSuccess: () => client.invalidateQueries({ queryKey: ["governance-settings"] }),
  });
}

export function useGovernanceNotifications() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["governance-notifications", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>("/governance/notifications", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

// ---- Agents ---------------------------------------------------------------

export function useAgentsOverview() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["agents-overview", orgId],
    queryFn: () =>
      api.get<Record<string, unknown>>("/agents/overview", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useAgents() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["agents", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>("/agents", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useAgent(id: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["agent", orgId, id],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/agents/${id}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId && id),
  });
}

export function useAgentExecutions(agentId?: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["agent-executions", orgId, agentId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>(
        `/agents/executions/list${agentId ? `?agent_id=${agentId}` : ""}`,
        token ?? undefined,
        orgId ?? undefined
      ),
    enabled: Boolean(token && orgId),
  });
}

export function useAgentExecution(id: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["agent-execution", orgId, id],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/agents/executions/${id}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId && id),
  });
}

export function useExecuteAgent() {
  const token = useToken();
  const orgId = useOrgId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.post(`/agents/${id}/execute`, body, token ?? undefined, orgId ?? undefined),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["agent-executions"] });
      client.invalidateQueries({ queryKey: ["agents-overview"] });
    },
  });
}

export function useWorkflows() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["workflows", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>("/workflows", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useWorkflowExecutions(workflowId?: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["workflow-executions", orgId, workflowId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>(
        `/workflows/executions/list${workflowId ? `?workflow_id=${workflowId}` : ""}`,
        token ?? undefined,
        orgId ?? undefined
      ),
    enabled: Boolean(token && orgId),
  });
}

export function useWorkflowExecution(id: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["workflow-execution", orgId, id],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/workflows/executions/${id}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId && id),
  });
}

// ---- Extensions -----------------------------------------------------------

export function useExtensionPackages(params?: Record<string, string>) {
  const token = useToken();
  const orgId = useOrgId();
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return useQuery({
    queryKey: ["extension-packages", orgId, params],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>(`/extensions/packages${qs}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useExtensionInstallations() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["extension-installations", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>("/extensions/installations", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useExtensionInstallation(id: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["extension-installation", orgId, id],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/extensions/installations/${id}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId && id),
  });
}

export function useTemplates(pluginType?: string) {
  const token = useToken();
  const orgId = useOrgId();
  const qs = pluginType ? `?plugin_type=${pluginType}` : "";
  return useQuery({
    queryKey: ["templates", orgId, pluginType],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>(`/templates${qs}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

// ---- Enterprise -----------------------------------------------------------

export function useEnterpriseOverview() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["enterprise-overview", orgId],
    queryFn: () =>
      api.get<Record<string, unknown>>("/enterprise/overview", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useWorkspaces() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["workspaces", orgId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>("/workspaces", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useWorkspace(id: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["workspace", orgId, id],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/workspaces/${id}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId && id),
  });
}

export function useProjects(workspaceId?: string) {
  const token = useToken();
  const orgId = useOrgId();
  const qs = workspaceId ? `?workspace_id=${workspaceId}` : "";
  return useQuery({
    queryKey: ["projects", orgId, workspaceId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>(`/projects${qs}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useProject(id: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["project", orgId, id],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/projects/${id}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId && id),
  });
}

export function useEnvironments(projectId: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["environments", orgId, projectId],
    queryFn: () =>
      api.get<Array<Record<string, unknown>>>(
        `/projects/${projectId}/environments`,
        token ?? undefined,
        orgId ?? undefined
      ),
    enabled: Boolean(token && orgId && projectId),
  });
}

export function useFleet() {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["fleet", orgId],
    queryFn: () =>
      api.get<Record<string, unknown>>("/fleet", token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId),
  });
}

export function useFleetInstance(id: string) {
  const token = useToken();
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["fleet-instance", orgId, id],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/fleet/${id}`, token ?? undefined, orgId ?? undefined),
    enabled: Boolean(token && orgId && id),
  });
}
