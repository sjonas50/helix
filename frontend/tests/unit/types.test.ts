import { describe, it, expect } from "vitest";
import type {
  Workflow,
  WorkflowStatus,
  ApprovalRequest,
  RiskLevel,
  MemoryRecord,
  Integration,
  AuditEvent,
  AutonomyLevel,
} from "@/types/api";
import { AUTONOMY_LABELS } from "@/types/api";
import type { WSEvent, WSEventType } from "@/types/ws";
import type { AuthUser, AuthSession } from "@/types/auth";

describe("API Types", () => {
  it("WorkflowStatus has 6 valid values", () => {
    const statuses: WorkflowStatus[] = [
      "PLANNING",
      "EXECUTING",
      "AWAITING_APPROVAL",
      "VERIFYING",
      "COMPLETE",
      "FAILED",
    ];
    expect(statuses).toHaveLength(6);
  });

  it("RiskLevel has 4 valid values", () => {
    const levels: RiskLevel[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
    expect(levels).toHaveLength(4);
  });

  it("Autonomy labels cover all 4 levels", () => {
    expect(Object.keys(AUTONOMY_LABELS)).toHaveLength(4);
    expect(AUTONOMY_LABELS[1]).toBe("Observe & Suggest");
    expect(AUTONOMY_LABELS[4]).toBe("Act Autonomously");
  });
});

describe("WebSocket Types", () => {
  it("WSEventType covers all event types", () => {
    const types: WSEventType[] = [
      "approval_request",
      "workflow_status",
      "agent_activity",
      "ack",
    ];
    expect(types).toHaveLength(4);
  });
});

describe("Auth Types", () => {
  it("AuthSession has required fields", () => {
    const session: AuthSession = {
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: true,
    };
    expect(session.isAuthenticated).toBe(false);
  });
});
