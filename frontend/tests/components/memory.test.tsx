import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryCard } from "@/components/memory/MemoryCard";
import { MemorySearch } from "@/components/memory/MemorySearch";
import type { MemoryRecord } from "@/types/api";

// Mock the API hooks
vi.mock("@/lib/api/memory", () => ({
  useMemorySearch: () => ({ data: null, isLoading: false }),
}));

const mockMemory: MemoryRecord = {
  id: "mem-1",
  org_id: "org-1",
  topic: "Deployment Policy",
  content:
    "All production deployments must go through the staging environment first and require approval from at least one senior engineer.",
  tags: ["deployment", "policy"],
  access_level: "PUBLIC",
  version: 3,
  valid_from: "2026-01-01T00:00:00Z",
  valid_until: null,
  created_at: new Date().toISOString(),
  similarity: 0.92,
};

describe("MemoryCard", () => {
  it("renders topic and content", () => {
    render(<MemoryCard memory={mockMemory} />);
    expect(screen.getByTestId("memory-topic").textContent).toBe(
      "Deployment Policy"
    );
    expect(screen.getByTestId("memory-content").textContent).toContain(
      "All production deployments"
    );
  });

  it("renders tags as badges", () => {
    render(<MemoryCard memory={mockMemory} />);
    expect(screen.getByText("deployment")).toBeDefined();
    expect(screen.getByText("policy")).toBeDefined();
  });

  it("renders version number", () => {
    render(<MemoryCard memory={mockMemory} />);
    expect(screen.getByText("v3")).toBeDefined();
  });

  it("shows green styling for PUBLIC access level", () => {
    render(<MemoryCard memory={mockMemory} />);
    const badge = screen.getByTestId("access-badge");
    expect(badge.textContent).toBe("PUBLIC");
    expect(badge.className).toContain("green");
  });

  it("shows yellow styling for ROLE_RESTRICTED access level", () => {
    const restricted = { ...mockMemory, access_level: "ROLE_RESTRICTED" as const };
    render(<MemoryCard memory={restricted} />);
    const badge = screen.getByTestId("access-badge");
    expect(badge.textContent).toBe("ROLE_RESTRICTED");
    expect(badge.className).toContain("yellow");
  });

  it("shows red styling for CONFIDENTIAL access level", () => {
    const confidential = { ...mockMemory, access_level: "CONFIDENTIAL" as const };
    render(<MemoryCard memory={confidential} />);
    const badge = screen.getByTestId("access-badge");
    expect(badge.textContent).toBe("CONFIDENTIAL");
    expect(badge.className).toContain("red");
  });

  it("truncates long content", () => {
    const longContent = { ...mockMemory, content: "A".repeat(300) };
    render(<MemoryCard memory={longContent} />);
    const content = screen.getByTestId("memory-content").textContent!;
    expect(content.endsWith("...")).toBe(true);
    expect(content.length).toBeLessThan(210);
  });
});

describe("MemorySearch", () => {
  it("renders search input", () => {
    render(<MemorySearch />);
    expect(screen.getByTestId("memory-search-input")).toBeDefined();
  });

  it("has correct placeholder text", () => {
    render(<MemorySearch />);
    const input = screen.getByTestId("memory-search-input") as HTMLInputElement;
    expect(input.placeholder).toBe("Search institutional memory...");
  });
});
