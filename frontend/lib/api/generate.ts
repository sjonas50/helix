"use client";

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface WorkflowNode {
  id: string;
  type: "trigger" | "action" | "condition" | "approval" | "agent";
  label: string;
  description: string;
  provider?: string | null;
  tool_name?: string | null;
  risk_level?: string | null;
  trigger_type?: string | null;
  agent_role?: string | null;
  condition_text?: string | null;
  sla_minutes?: number | null;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface GeneratedWorkflow {
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  integrations_used: string[];
  estimated_risk: string;
}

export function useGenerateWorkflow() {
  return useMutation({
    mutationFn: (description: string) =>
      apiClient<GeneratedWorkflow>("/generate/workflow", {
        method: "POST",
        body: JSON.stringify({ description }),
      }),
  });
}
