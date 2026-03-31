"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { UsageStats } from "@/types/api";

export function useUsageStats() {
  return useQuery({
    queryKey: ["usage"],
    queryFn: () => apiClient<UsageStats>("/usage/stats"),
  });
}
