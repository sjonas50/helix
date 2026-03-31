"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { ApprovalRequest, ApprovalDecision } from "@/types/api";

export function useApprovals() {
  return useQuery({
    queryKey: ["approvals"],
    queryFn: () => apiClient<ApprovalRequest[]>("/approvals/"),
  });
}

export function useDecideApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      decision,
    }: {
      id: string;
      decision: ApprovalDecision;
    }) =>
      apiClient<ApprovalRequest>(`/approvals/${id}/decide`, {
        method: "POST",
        body: JSON.stringify(decision),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals"] });
      qc.invalidateQueries({ queryKey: ["audit"] });
    },
  });
}
