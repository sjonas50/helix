import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock recharts to avoid canvas issues in jsdom
vi.mock("recharts", () => {
  const MockContainer = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  );
  const MockChart = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="mock-chart">{children}</div>
  );
  const MockElement = () => <div />;
  return {
    ResponsiveContainer: MockContainer,
    BarChart: MockChart,
    Bar: MockElement,
    XAxis: MockElement,
    YAxis: MockElement,
    CartesianGrid: MockElement,
    Tooltip: MockElement,
    LineChart: MockChart,
    Line: MockElement,
  };
});

// Mock API hooks
vi.mock("@/lib/api/settings", () => ({
  useUsageStats: () => ({ data: null, isLoading: false }),
}));

// Dynamic imports after mocks are set up
import BillingPage from "@/app/(dashboard)/settings/billing/page";
import MembersPage from "@/app/(dashboard)/settings/members/page";

describe("BillingPage", () => {
  it("renders summary cards", () => {
    render(<BillingPage />);
    expect(screen.getByText("Total Tokens")).toBeDefined();
    expect(screen.getByText("Total Cost")).toBeDefined();
    expect(screen.getByText("Most Expensive Workflow")).toBeDefined();
  });

  it("renders chart sections", () => {
    render(<BillingPage />);
    expect(screen.getByText("Token Usage by Model")).toBeDefined();
    expect(screen.getByText("Daily Cost Trend")).toBeDefined();
  });

  it("renders chart containers", () => {
    render(<BillingPage />);
    expect(screen.getByTestId("bar-chart")).toBeDefined();
    expect(screen.getByTestId("line-chart")).toBeDefined();
  });
});

describe("MembersPage", () => {
  it("renders table headers", () => {
    render(<MembersPage />);
    expect(screen.getByText("Name")).toBeDefined();
    expect(screen.getByText("Email")).toBeDefined();
    expect(screen.getByText("Role")).toBeDefined();
    expect(screen.getByText("Last Active")).toBeDefined();
  });

  it("renders mock member data", () => {
    render(<MembersPage />);
    expect(screen.getByText("Sarah Chen")).toBeDefined();
    expect(screen.getByText("james@acme.com")).toBeDefined();
  });

  it("renders invite button", () => {
    render(<MembersPage />);
    expect(screen.getByText("Invite Member")).toBeDefined();
  });
});
