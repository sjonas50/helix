/**
 * TypeScript types matching backend Pydantic schemas.
 * Keep in sync with src/helix/api/schemas/ and src/helix/db/models.py.
 */

// --- Orgs ---
export interface Org {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: string;
  on_prem: boolean;
  created_at: string;
}

// --- Users ---
export interface User {
  id: string;
  org_id: string;
  email: string;
  display_name: string | null;
  roles: string[];
}

// --- Workflows ---
export type WorkflowStatus =
  | "PLANNING"
  | "EXECUTING"
  | "AWAITING_APPROVAL"
  | "VERIFYING"
  | "COMPLETE"
  | "FAILED";

export interface Workflow {
  id: string;
  org_id: string;
  name: string;
  description: string;
  template_id: string | null;
  status: WorkflowStatus;
  coordinator_agent_id: string | null;
  token_usage: Record<string, number> | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface WorkflowCreate {
  template_id?: string;
  initial_context?: Record<string, unknown>;
}

// --- Agents ---
export type AgentRole = "coordinator" | "researcher" | "implementer" | "verifier";

export interface Agent {
  id: string;
  workflow_id: string;
  role: AgentRole;
  model_id: string;
  status: string;
  spawned_by: string | null;
  hierarchy_depth: number;
  token_usage: Record<string, number> | null;
  created_at: string;
  terminated_at: string | null;
}

// --- Approvals ---
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "ESCALATED" | "EXPIRED";

export interface ApprovalRequest {
  id: string;
  workflow_id: string;
  org_id: string;
  action_description: string;
  risk_level: RiskLevel;
  status: ApprovalStatus;
  decided_by: string | null;
  decision_reason: string | null;
  sla_deadline: string | null;
  created_at: string;
  decided_at: string | null;
}

export interface ApprovalDecision {
  decision: "APPROVED" | "REJECTED";
  reason?: string;
}

// --- Memory ---
export type AccessLevel = "PUBLIC" | "ROLE_RESTRICTED" | "CONFIDENTIAL";

export interface MemoryRecord {
  id: string;
  org_id: string;
  topic: string;
  content: string;
  tags: string[] | null;
  access_level: AccessLevel;
  version: number;
  valid_from: string;
  valid_until: string | null;
  created_at: string;
  similarity?: number;
}

export interface MemoryCreate {
  topic: string;
  content: string;
  tags?: string[];
  access_level?: AccessLevel;
  allowed_roles?: string[];
}

export interface MemoryQuery {
  query: string;
  limit?: number;
  access_level?: AccessLevel;
  topic_filter?: string;
}

// --- Integrations ---
export interface Integration {
  id: string;
  org_id: string;
  provider: string;
  connector_type: string;
  enabled: boolean;
  rate_limit_per_hour: number;
  created_at: string;
  updated_at: string;
}

export interface IntegrationCreate {
  provider: string;
  connector_type?: "composio" | "nango" | "custom";
  config?: Record<string, unknown>;
  rate_limit_per_hour?: number;
}

// --- Audit ---
export interface AuditEvent {
  id: string;
  org_id: string;
  user_id: string | null;
  agent_id: string | null;
  event_type: string;
  resource_type: string | null;
  resource_id: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditResponse {
  events: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
}

// --- Autonomy ---
export type AutonomyLevel = 1 | 2 | 3 | 4;
export const AUTONOMY_LABELS: Record<AutonomyLevel, string> = {
  1: "Observe & Suggest",
  2: "Plan & Propose",
  3: "Act with Confirmation",
  4: "Act Autonomously",
};

// --- Usage ---
export interface UsageStats {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  by_model: Record<string, { tokens: number; cost: number }>;
  by_workflow: Record<string, { tokens: number; cost: number }>;
}
