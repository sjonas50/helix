"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { Agent, AuditEvent } from "@/types/api";

export function useAgents(workflowId: string) {
  return useQuery({
    queryKey: ["agents", workflowId],
    queryFn: () =>
      apiClient<Agent[]>(`/workflows/${workflowId}/agents`),
    enabled: !!workflowId,
  });
}

export function useAgentMessages(agentId: string) {
  return useQuery({
    queryKey: ["agents", agentId, "messages"],
    queryFn: () =>
      apiClient<AuditEvent[]>(`/agents/${agentId}/messages`),
    enabled: !!agentId,
  });
}
