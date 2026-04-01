import { describe, it, expect, vi, afterEach } from "vitest";
import {
  decodeJWTPayload,
  isTokenExpired,
  getTokenOrgId,
} from "@/lib/auth/tokenUtils";

/** Helper: build a fake JWT with a given payload object. */
function makeJWT(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `${header}.${body}.fake-signature`;
}

describe("decodeJWTPayload", () => {
  it("decodes a valid JWT payload", () => {
    const payload = { sub: "user-1", org_id: "org-1", email: "a@b.com" };
    const token = makeJWT(payload);
    const decoded = decodeJWTPayload(token);
    expect(decoded).toEqual(payload);
  });

  it("returns null for completely invalid token", () => {
    expect(decodeJWTPayload("not-a-jwt")).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(decodeJWTPayload("")).toBeNull();
  });

  it("handles base64url characters (- and _) correctly", () => {
    // Create a payload that, when base64-encoded, contains + and /
    // so the base64url encoding will use - and _ instead
    const payload = { data: "test+value/with=special>>>chars???" };
    const token = makeJWT(payload);
    const decoded = decodeJWTPayload(token);
    expect(decoded).toEqual(payload);
  });
});

describe("isTokenExpired", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns false when exp is in the future", () => {
    const futureExp = Math.floor(Date.now() / 1000) + 3600; // 1 hour from now
    const token = makeJWT({ exp: futureExp });
    expect(isTokenExpired(token)).toBe(false);
  });

  it("returns true when exp is in the past", () => {
    const pastExp = Math.floor(Date.now() / 1000) - 60; // 1 minute ago
    const token = makeJWT({ exp: pastExp });
    expect(isTokenExpired(token)).toBe(true);
  });

  it("returns true when token is within 30s buffer of expiry", () => {
    // Token expires 20 seconds from now — within the 30s buffer
    const nearExp = Math.floor(Date.now() / 1000) + 20;
    const token = makeJWT({ exp: nearExp });
    expect(isTokenExpired(token)).toBe(true);
  });

  it("returns false when token is just outside the 30s buffer", () => {
    // Token expires 60 seconds from now — outside the 30s buffer
    const safeExp = Math.floor(Date.now() / 1000) + 60;
    const token = makeJWT({ exp: safeExp });
    expect(isTokenExpired(token)).toBe(false);
  });

  it("returns true when exp is missing", () => {
    const token = makeJWT({ sub: "user-1" });
    expect(isTokenExpired(token)).toBe(true);
  });

  it("returns true for invalid token", () => {
    expect(isTokenExpired("garbage")).toBe(true);
  });
});

describe("getTokenOrgId", () => {
  it("returns org_id from token", () => {
    const token = makeJWT({ org_id: "org-abc" });
    expect(getTokenOrgId(token)).toBe("org-abc");
  });

  it("returns null when org_id is missing", () => {
    const token = makeJWT({ sub: "user-1" });
    expect(getTokenOrgId(token)).toBeNull();
  });

  it("returns null for invalid token", () => {
    expect(getTokenOrgId("bad-token")).toBeNull();
  });
});
