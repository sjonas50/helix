"use client";

import { create } from "zustand";
import type { AuthUser, AuthSession } from "@/types/auth";
import { decodeJWTPayload, isTokenExpired } from "@/lib/auth/tokenUtils";

interface AuthStore extends AuthSession {
  login: (token: string) => void;
  logout: () => void;
  /** Check if the current access token is expired (with 30s buffer). */
  isTokenExpired: () => boolean;
  /** Return the token only if it is still valid; otherwise return null. */
  getValidToken: () => string | null;
}

export const useAuth = create<AuthStore>((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  login: (token: string) => {
    // Decode JWT payload (base64url-safe) — no verification on client side
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
  logout: () =>
    set({ user: null, accessToken: null, isAuthenticated: false }),
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
