/**
 * Auth types for WorkOS AuthKit + JWT.
 */

export interface JWTClaims {
  sub: string; // user_id
  org_id: string;
  roles: string[];
  token_type: "user" | "agent";
  exp: number;
  iat: number;
}

export interface AuthUser {
  id: string;
  org_id: string;
  email: string;
  display_name: string | null;
  roles: string[];
}

export interface AuthSession {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
