/**
 * JWT token utilities — expiry checking, safe base64url decode.
 */

export function decodeJWTPayload(token: string): Record<string, unknown> | null {
  try {
    // Handle base64url encoding (JWT uses - and _ instead of + and /)
    const base64 = token.split(".")[1]
      .replace(/-/g, "+")
      .replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - base64.length % 4) % 4);
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJWTPayload(token);
  if (!payload || typeof payload.exp !== "number") return true;
  // Add 30 second buffer to avoid edge cases
  return Date.now() / 1000 > payload.exp - 30;
}

export function getTokenOrgId(token: string): string | null {
  const payload = decodeJWTPayload(token);
  return (payload?.org_id as string) ?? null;
}
