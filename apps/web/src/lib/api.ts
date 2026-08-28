// Typed HTTP client for the ModelBridge backend.
//
// In development the Next.js rewrite routes /api/* to the FastAPI backend, so
// we default to "/api". Set NEXT_PUBLIC_API_URL to an absolute URL to call the
// backend directly (e.g. http://localhost:8000) in other environments.

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string;
  orgId?: string | null;
}

function stripBase(path: string): string {
  // Callers always pass a backend path starting with "/" (e.g. "/providers").
  return path;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (options.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }
  if (options.orgId) {
    headers["X-Organization-ID"] = options.orgId;
  }

  const response = await fetch(`${API_BASE}${stripBase(path)}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    let code: string | undefined;
    try {
      const data = await response.json();
      if (data.detail) {
        message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      } else if (data.error?.message) {
        message = data.error.message;
        code = data.error.code;
      }
    } catch {
      // ignore JSON parse errors; keep the generic message
    }
    if (response.status === 401) {
      // Let the caller redirect to login.
      throw new ApiError("Unauthorized", 401, code);
    }
    throw new ApiError(message, response.status, code);
  }

  // 204 No Content and other empty bodies have no JSON payload.
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, token?: string, orgId?: string | null) =>
    apiRequest<T>(path, { token, orgId }),
  post: <T>(path: string, body?: unknown, token?: string, orgId?: string | null) =>
    apiRequest<T>(path, { method: "POST", body, token, orgId }),
  patch: <T>(path: string, body?: unknown, token?: string, orgId?: string | null) =>
    apiRequest<T>(path, { method: "PATCH", body, token, orgId }),
  put: <T>(path: string, body?: unknown, token?: string, orgId?: string | null) =>
    apiRequest<T>(path, { method: "PUT", body, token, orgId }),
  delete: <T>(path: string, token?: string, orgId?: string | null) =>
    apiRequest<T>(path, { method: "DELETE", token, orgId }),
};
