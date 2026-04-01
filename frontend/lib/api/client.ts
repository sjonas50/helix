import { isTokenExpired } from "@/lib/auth/tokenUtils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/proxy";

export async function apiClient<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const { useAuth } = await import("@/lib/auth/useAuth");
  const token = useAuth.getState().accessToken;

  // If token is expired, log out and redirect before making the request
  if (token && isTokenExpired(token)) {
    useAuth.getState().logout();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Token expired");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (res.status === 401) {
    useAuth.getState().logout();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
