/**
 * WebSocket event types matching FastAPI emission.
 */

export type WSEventType = "approval_request" | "workflow_status" | "agent_activity" | "ack";

export interface WSEventBase {
  type: WSEventType;
  timestamp: string;
}

export interface ApprovalRequestEvent extends WSEventBase {
  type: "approval_request";
  data: {
    approval_id: string;
    workflow_id: string;
    action_description: string;
    risk_level: string;
    sla_deadline: string | null;
  };
}

export interface WorkflowStatusEvent extends WSEventBase {
  type: "workflow_status";
  data: {
    workflow_id: string;
    status: string;
    phase: string;
  };
}

export interface AgentActivityEvent extends WSEventBase {
  type: "agent_activity";
  data: {
    agent_id: string;
    workflow_id: string;
    action: string;
    description: string;
  };
}

export interface AckEvent extends WSEventBase {
  type: "ack";
  data: Record<string, unknown>;
}

export type WSEvent =
  | ApprovalRequestEvent
  | WorkflowStatusEvent
  | AgentActivityEvent
  | AckEvent;
