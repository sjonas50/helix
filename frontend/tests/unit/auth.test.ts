import { describe, it, expect } from "vitest";
import { hasRole, requireRole } from "@/lib/auth/guards";
import type { AuthUser } from "@/types/auth";

const adminUser: AuthUser = {
  id: "usr_001",
  org_id: "org_001",
  email: "admin@example.com",
  display_name: "Admin User",
  roles: ["admin", "operator"],
};

const viewerUser: AuthUser = {
  id: "usr_002",
  org_id: "org_001",
  email: "viewer@example.com",
  display_name: "Viewer",
  roles: ["viewer"],
};

const noRolesUser: AuthUser = {
  id: "usr_003",
  org_id: "org_001",
  email: "noroles@example.com",
  display_name: null,
  roles: [],
};

describe("hasRole", () => {
  it("returns true when user has one of the required roles", () => {
    expect(hasRole(adminUser, "admin")).toBe(true);
    expect(hasRole(adminUser, "operator")).toBe(true);
    expect(hasRole(adminUser, "viewer", "admin")).toBe(true);
  });

  it("returns false when user does not have any required role", () => {
    expect(hasRole(viewerUser, "admin")).toBe(false);
    expect(hasRole(viewerUser, "admin", "operator")).toBe(false);
  });

  it("returns false for null user", () => {
    expect(hasRole(null, "admin")).toBe(false);
  });

  it("returns false for user with empty roles", () => {
    expect(hasRole(noRolesUser, "admin")).toBe(false);
  });

  it("returns false when no roles are required", () => {
    // No roles passed = roles.some() returns false
    expect(hasRole(adminUser)).toBe(false);
  });
});

describe("requireRole", () => {
  it("does not throw when user has a required role", () => {
    expect(() => requireRole(adminUser, "admin")).not.toThrow();
    expect(() => requireRole(adminUser, "viewer", "operator")).not.toThrow();
  });

  it("throws when user lacks the required role", () => {
    expect(() => requireRole(viewerUser, "admin")).toThrow(
      "Requires one of: admin"
    );
  });

  it("throws for null user", () => {
    expect(() => requireRole(null, "admin")).toThrow();
  });
});
