import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiClient } from "@/lib/api/client";

// Mock useAuth store
const mockLogout = vi.fn();
let mockToken: string | null = "test-token";

vi.mock("@/lib/auth/useAuth", () => ({
  useAuth: {
    getState: () => ({
      accessToken: mockToken,
      logout: mockLogout,
    }),
  },
}));

describe("apiClient", () => {
  beforeEach(() => {
    mockToken = "test-token";
    mockLogout.mockClear();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches Authorization header when token is present", async () => {
    const mockResponse = { id: "1", name: "test" };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await apiClient("/workflows/");

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/proxy/workflows/",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
          "Content-Type": "application/json",
        }),
      })
    );
    expect(result).toEqual(mockResponse);
  });

  it("does not attach Authorization header when no token", async () => {
    mockToken = null;
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await apiClient("/workflows/");

    const callHeaders = (global.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][1].headers;
    expect(callHeaders).not.toHaveProperty("Authorization");
  });

  it("handles 401 by logging out and throwing", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Unauthorized" }),
    });

    await expect(apiClient("/workflows/")).rejects.toThrow("Unauthorized");
    expect(mockLogout).toHaveBeenCalled();
  });

  it("handles non-JSON error responses", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.reject(new Error("not json")),
    });

    await expect(apiClient("/workflows/")).rejects.toThrow(
      "Internal Server Error"
    );
  });

  it("returns undefined for 204 responses", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 204,
    });

    const result = await apiClient("/workflows/123");
    expect(result).toBeUndefined();
  });
});
