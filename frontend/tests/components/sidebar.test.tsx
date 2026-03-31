import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sidebar } from "@/components/shared/Sidebar";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("Sidebar", () => {
  it("renders all navigation items", () => {
    render(<Sidebar />);

    expect(screen.getByText("Dashboard")).toBeDefined();
    expect(screen.getByText("Workflows")).toBeDefined();
    expect(screen.getByText("Approvals")).toBeDefined();
    expect(screen.getByText("Memory")).toBeDefined();
    expect(screen.getByText("Integrations")).toBeDefined();
    expect(screen.getByText("Audit")).toBeDefined();
    expect(screen.getByText("Settings")).toBeDefined();
  });

  it("renders approval badge when pendingApprovals > 0", () => {
    render(<Sidebar pendingApprovals={3} />);

    expect(screen.getByText("3")).toBeDefined();
  });

  it("does not render approval badge when pendingApprovals is 0", () => {
    render(<Sidebar pendingApprovals={0} />);

    // The badge should not appear
    expect(screen.queryByText("0")).toBeNull();
  });

  it("highlights the active link based on pathname", () => {
    render(<Sidebar />);

    const dashboardLink = screen.getByText("Dashboard").closest("a");
    expect(dashboardLink?.className).toContain("bg-sidebar-accent");
  });
});
