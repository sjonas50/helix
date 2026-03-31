import type { AuthUser } from "@/types/auth";

export function hasRole(user: AuthUser | null, ...roles: string[]): boolean {
  if (!user) return false;
  return roles.some((role) => user.roles.includes(role));
}

export function requireRole(user: AuthUser | null, ...roles: string[]): void {
  if (!hasRole(user, ...roles)) {
    throw new Error(`Requires one of: ${roles.join(", ")}`);
  }
}
