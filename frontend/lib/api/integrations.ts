"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { Integration, IntegrationCreate } from "@/types/api";

export function useIntegrations() {
  return useQuery({
    queryKey: ["integrations"],
    queryFn: () => apiClient<Integration[]>("/integrations/"),
  });
}

export function useProviders() {
  return useQuery({
    queryKey: ["integrations", "providers"],
    queryFn: () => apiClient<string[]>("/integrations/providers"),
  });
}

export function useConnectIntegration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: IntegrationCreate) =>
      apiClient<Integration>("/integrations/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations"] }),
  });
}
