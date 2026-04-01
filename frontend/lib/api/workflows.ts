"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { Workflow, WorkflowCreate } from "@/types/api";

export function useWorkflows() {
  return useQuery({
    queryKey: ["workflows"],
    queryFn: () => apiClient<Workflow[]>("/workflows/"),
  });
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: ["workflows", id],
    queryFn: () => apiClient<Workflow>(`/workflows/${id}`),
  });
}

export function useCreateWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkflowCreate) =>
      apiClient<Workflow>("/workflows/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

export interface DeployWorkflowRequest {
  name: string;
  description: string;
  workflow_json: string;
}

export function useDeployWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DeployWorkflowRequest) =>
      apiClient<{ id: string; status: string; name: string }>("/workflows/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

export function useRunWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (workflowId: string) =>
      apiClient<{ workflow_id: string; status: string; message: string }>(
        `/workflows/${workflowId}/run`,
        { method: "POST" }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}
