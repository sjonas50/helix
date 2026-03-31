"use client";

import { MemorySearch } from "@/components/memory/MemorySearch";

export default function MemoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Institutional Memory
        </h1>
        <p className="text-muted-foreground">
          Semantic knowledge store for your organization. Memory records capture
          decisions, policies, and institutional knowledge that agents use to
          stay aligned with your workflows.
        </p>
      </div>

      <MemorySearch />
    </div>
  );
}
