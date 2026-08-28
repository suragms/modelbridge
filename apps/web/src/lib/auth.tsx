"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { api, ApiError } from "./api";
import type { TokenResponse, User } from "./types";

const TOKEN_KEY = "mb_token";
const USER_KEY = "mb_user";
const ORG_KEY = "mb_org_id";

interface AuthContextValue {
  token: string | null;
  user: User | null;
  activeOrgId: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  setActiveOrgId: (orgId: string | null) => void;
  switchOrganization: (orgId: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [activeOrgId, setActiveOrgIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
      setUser(readStoredUser());
      setActiveOrgIdState(localStorage.getItem(ORG_KEY));
    }
    setLoading(false);
  }, []);

  const setActiveOrgId = useCallback((orgId: string | null) => {
    if (orgId) localStorage.setItem(ORG_KEY, orgId);
    else localStorage.removeItem(ORG_KEY);
    setActiveOrgIdState(orgId);
  }, []);

  const persist = useCallback((t: TokenResponse) => {
    localStorage.setItem(TOKEN_KEY, t.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(t.user));
    if (t.user.organization_id) {
      localStorage.setItem(ORG_KEY, t.user.organization_id);
      setActiveOrgIdState(t.user.organization_id);
    }
    setToken(t.access_token);
    setUser(t.user);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await api.post<TokenResponse>("/auth/login", { email, password });
      persist(data);
    },
    [persist]
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const data = await api.post<TokenResponse>("/auth/register", {
        email,
        password,
        full_name: fullName,
      });
      persist(data);
    },
    [persist]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(ORG_KEY);
    setToken(null);
    setUser(null);
    setActiveOrgIdState(null);
  }, []);

  const switchOrganization = useCallback(
    async (orgId: string) => {
      const data = await api.post<TokenResponse>(
        `/organizations/current/switch?organization_id=${orgId}`,
        undefined,
        token ?? undefined
      );
      persist(data);
    },
    [token, persist]
  );

  const value = useMemo(
    () => ({
      token,
      user,
      activeOrgId,
      loading,
      login,
      register,
      logout,
      setActiveOrgId,
      switchOrganization,
    }),
    [token, user, activeOrgId, loading, login, register, logout, setActiveOrgId, switchOrganization]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

/**
 * Client-side guard for protected routes. Redirects to /login when the user is
 * not authenticated (and defers rendering while auth is still restoring).
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, token, router]);

  if (loading || !token) {
    return null;
  }
  return <>{children}</>;
}

export { ApiError };
