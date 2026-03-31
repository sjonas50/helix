"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { MemoryRecord, MemoryCreate, MemoryQuery } from "@/types/api";

export function useMemorySearch(query: MemoryQuery | null) {
  return useQuery({
    queryKey: ["memory", "search", query],
    queryFn: () =>
      apiClient<MemoryRecord[]>("/memory/search", {
        method: "POST",
        body: JSON.stringify(query),
      }),
    enabled: !!query?.query,
  });
}

export function useCreateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MemoryCreate) =>
      apiClient<MemoryRecord>("/memory/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memory"] }),
  });
}
