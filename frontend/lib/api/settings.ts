"use client";

import { useQuery } from "@tanstack/react-query";
import type { UsageStats } from "@/types/api";

// Note: /usage/stats endpoint not yet implemented on backend.
// Returns mock data for development. Wire to real endpoint when available.
const MOCK_USAGE: UsageStats = {
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_cost_usd: 0,
  by_model: {},
  by_workflow: {},
};

export function useUsageStats() {
  return useQuery({
    queryKey: ["usage"],
    queryFn: async () => MOCK_USAGE,
  });
}
