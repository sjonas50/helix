"use client";

import { create } from "zustand";
import type { AuthUser, AuthSession } from "@/types/auth";

interface AuthStore extends AuthSession {
  login: (token: string) => void;
  logout: () => void;
}

export const useAuth = create<AuthStore>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  login: (token: string) => {
    // Decode JWT payload (base64) — no verification on client side
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      const user: AuthUser = {
        id: payload.sub,
        org_id: payload.org_id,
        email: payload.email || "",
        display_name: payload.display_name || null,
        roles: payload.roles || [],
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
}));
