"use client";

import { create } from "zustand";
import type { AuthUser, AuthSession } from "@/types/auth";
import { decodeJWTPayload, isTokenExpired } from "@/lib/auth/tokenUtils";

const TOKEN_KEY = "helix_token";

function loadPersistedToken(): { user: AuthUser | null; accessToken: string | null; isAuthenticated: boolean } {
  if (typeof window === "undefined") {
    return { user: null, accessToken: null, isAuthenticated: false };
  }
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token || isTokenExpired(token)) {
    localStorage.removeItem(TOKEN_KEY);
    return { user: null, accessToken: null, isAuthenticated: false };
  }
  const payload = decodeJWTPayload(token);
  if (!payload) {
    localStorage.removeItem(TOKEN_KEY);
    return { user: null, accessToken: null, isAuthenticated: false };
  }
  return {
    user: {
      id: payload.sub as string,
      org_id: payload.org_id as string,
      email: (payload.email as string) || "",
      display_name: (payload.display_name as string) || null,
      roles: (payload.roles as string[]) || [],
    },
    accessToken: token,
    isAuthenticated: true,
  };
}

interface AuthStore extends AuthSession {
  login: (token: string) => void;
  logout: () => void;
  isTokenExpired: () => boolean;
  getValidToken: () => string | null;
}

const persisted = loadPersistedToken();

export const useAuth = create<AuthStore>((set, get) => ({
  user: persisted.user,
  accessToken: persisted.accessToken,
  isAuthenticated: persisted.isAuthenticated,
  isLoading: false,
  login: (token: string) => {
    try {
      const payload = decodeJWTPayload(token);
      if (!payload) throw new Error("Invalid token payload");
      const user: AuthUser = {
        id: payload.sub as string,
        org_id: payload.org_id as string,
        email: (payload.email as string) || "",
        display_name: (payload.display_name as string) || null,
        roles: (payload.roles as string[]) || [],
      };
      if (typeof window !== "undefined") {
        localStorage.setItem(TOKEN_KEY, token);
      }
      set({
        user,
        accessToken: token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
    }
    set({ user: null, accessToken: null, isAuthenticated: false });
  },
  isTokenExpired: () => {
    const token = get().accessToken;
    if (!token) return true;
    return isTokenExpired(token);
  },
  getValidToken: () => {
    const token = get().accessToken;
    if (!token) return null;
    return isTokenExpired(token) ? null : token;
  },
}));
