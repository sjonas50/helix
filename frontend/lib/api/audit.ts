"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { AuditResponse } from "@/types/api";

interface AuditParams {
  limit?: number;
  offset?: number;
  event_type?: string;
  resource_type?: string;
}

export function useAuditLog(params?: AuditParams) {
  return useQuery({
    queryKey: ["audit", params],
    queryFn: () => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.set("limit", String(params.limit));
      if (params?.offset) searchParams.set("offset", String(params.offset));
      if (params?.event_type)
        searchParams.set("event_type", params.event_type);
      if (params?.resource_type)
        searchParams.set("resource_type", params.resource_type);
      const qs = searchParams.toString();
      return apiClient<AuditResponse>(`/audit/events${qs ? `?${qs}` : ""}`);
    },
  });
}

export function useUndoAction() {
  const qc = useQueryClient();
  return useMutation({
    // Note: undo endpoint not yet implemented on backend — placeholder
    mutationFn: (eventId: string) =>
      apiClient<void>(`/audit/events/${eventId}/undo`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["audit"] }),
  });
}
