import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ApprovalCard } from "@/components/approval/ApprovalCard";
import { ApprovalBadge } from "@/components/approval/ApprovalBadge";
import type { ApprovalRequest } from "@/types/api";

const mockApproval: ApprovalRequest = {
  id: "apr-1",
  workflow_id: "wf-1",
  org_id: "org-1",
  action_description: "Deploy to production",
  risk_level: "HIGH",
  status: "PENDING",
  decided_by: null,
  decision_reason: "Triggered by schedule",
  sla_deadline: new Date(Date.now() + 3600_000 * 2).toISOString(),
  created_at: new Date().toISOString(),
  decided_at: null,
};

describe("ApprovalCard", () => {
  const onApprove = vi.fn();
  const onModify = vi.fn();
  const onReject = vi.fn();

  it("renders approval data", () => {
    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={onApprove}
        onModify={onModify}
        onReject={onReject}
      />
    );

    expect(screen.getByText("Deploy to production")).toBeDefined();
    expect(screen.getByText("Triggered by schedule")).toBeDefined();
  });

  it("renders all 3 action buttons", () => {
    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={onApprove}
        onModify={onModify}
        onReject={onReject}
      />
    );

    expect(screen.getByTestId("approve-btn")).toBeDefined();
    expect(screen.getByTestId("modify-btn")).toBeDefined();
    expect(screen.getByTestId("reject-btn")).toBeDefined();
  });

  it("shows correct risk level badge", () => {
    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={onApprove}
        onModify={onModify}
        onReject={onReject}
      />
    );

    const badge = screen.getByTestId("risk-badge");
    expect(badge.textContent).toBe("HIGH");
    expect(badge.className).toContain("orange");
  });

  it("shows green badge for LOW risk", () => {
    const lowApproval = { ...mockApproval, risk_level: "LOW" as const };
    render(
      <ApprovalCard
        approval={lowApproval}
        onApprove={onApprove}
        onModify={onModify}
        onReject={onReject}
      />
    );

    const badge = screen.getByTestId("risk-badge");
    expect(badge.className).toContain("green");
  });
});

describe("ApprovalBadge", () => {
  it("shows count when greater than 0", () => {
    render(<ApprovalBadge count={5} />);
    expect(screen.getByText("5")).toBeDefined();
  });

  it("does not render when count is 0", () => {
    const { container } = render(<ApprovalBadge count={0} />);
    expect(container.innerHTML).toBe("");
  });

  it("shows 99+ for large counts", () => {
    render(<ApprovalBadge count={150} />);
    expect(screen.getByText("99+")).toBeDefined();
  });
});
