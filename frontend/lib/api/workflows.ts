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
