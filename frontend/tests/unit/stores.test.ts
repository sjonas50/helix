import { describe, it, expect, beforeEach } from "vitest";
import { useUIStore } from "@/lib/store/uiStore";
import { useWSStore } from "@/lib/store/wsStore";
import { useAuth } from "@/lib/auth/useAuth";

describe("useUIStore", () => {
  beforeEach(() => {
    useUIStore.setState({ sidebarCollapsed: false });
  });

  it("starts with sidebar expanded", () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  it("toggles sidebar state", () => {
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);

    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });
});

describe("useWSStore", () => {
  beforeEach(() => {
    useWSStore.setState({ connected: false, lastEventAt: null });
  });

  it("starts disconnected with no last event", () => {
    const state = useWSStore.getState();
    expect(state.connected).toBe(false);
    expect(state.lastEventAt).toBeNull();
  });

  it("sets connected state", () => {
    useWSStore.getState().setConnected(true);
    expect(useWSStore.getState().connected).toBe(true);

    useWSStore.getState().setConnected(false);
    expect(useWSStore.getState().connected).toBe(false);
  });

  it("sets lastEventAt to ISO string", () => {
    useWSStore.getState().setLastEvent();
    const ts = useWSStore.getState().lastEventAt;
    expect(ts).toBeTruthy();
    expect(new Date(ts!).toISOString()).toBe(ts);
  });
});

describe("useAuth", () => {
  beforeEach(() => {
    useAuth.setState({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("starts unauthenticated", () => {
    const state = useAuth.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
  });

  it("login decodes JWT and sets user", () => {
    // Build a fake JWT: header.payload.signature
    const payload = {
      sub: "user-1",
      org_id: "org-1",
      email: "test@example.com",
      display_name: "Test User",
      roles: ["admin"],
    };
    const token = `header.${btoa(JSON.stringify(payload))}.signature`;

    useAuth.getState().login(token);

    const state = useAuth.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe(token);
    expect(state.user).toEqual({
      id: "user-1",
      org_id: "org-1",
      email: "test@example.com",
      display_name: "Test User",
      roles: ["admin"],
    });
  });

  it("logout clears state", () => {
    const payload = { sub: "u1", org_id: "o1", roles: [] };
    const token = `h.${btoa(JSON.stringify(payload))}.s`;
    useAuth.getState().login(token);
    expect(useAuth.getState().isAuthenticated).toBe(true);

    useAuth.getState().logout();

    const state = useAuth.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
  });

  it("login with invalid token resets to unauthenticated", () => {
    useAuth.getState().login("not-a-valid-jwt");
    expect(useAuth.getState().isAuthenticated).toBe(false);
    expect(useAuth.getState().user).toBeNull();
  });
});
