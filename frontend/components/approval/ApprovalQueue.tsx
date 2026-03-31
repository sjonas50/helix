"use client";

import { useState, useMemo } from "react";
import { useApprovals, useDecideApproval } from "@/lib/api/approvals";
import { ApprovalCard } from "./ApprovalCard";
import { ModifyDrawer } from "./ModifyDrawer";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle } from "lucide-react";
import type { ApprovalRequest, RiskLevel } from "@/types/api";

const RISK_FILTERS = ["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
type RiskFilter = (typeof RISK_FILTERS)[number];

export function ApprovalQueue() {
  const { data: approvals, isLoading } = useApprovals();
  const decide = useDecideApproval();
  const [filter, setFilter] = useState<RiskFilter>("ALL");
  const [modifyTarget, setModifyTarget] = useState<ApprovalRequest | null>(
    null
  );

  const pending = useMemo(() => {
    if (!approvals) return [];
    return approvals
      .filter((a) => a.status === "PENDING")
      .sort((a, b) => {
        if (!a.sla_deadline) return 1;
        if (!b.sla_deadline) return -1;
        return (
          new Date(a.sla_deadline).getTime() -
          new Date(b.sla_deadline).getTime()
        );
      });
  }, [approvals]);

  const filtered = useMemo(() => {
    if (filter === "ALL") return pending;
    return pending.filter((a) => a.risk_level === filter);
  }, [pending, filter]);

  const lowRiskItems = useMemo(
    () => pending.filter((a) => a.risk_level === "LOW"),
    [pending]
  );

  function handleApprove(id: string) {
    decide.mutate({ id, decision: { decision: "APPROVED" } });
  }

  function handleReject(id: string) {
    decide.mutate({
      id,
      decision: { decision: "REJECTED", reason: "Rejected by user" },
    });
  }

  function handleModifySubmit(id: string, reason: string) {
    decide.mutate({
      id,
      decision: { decision: "APPROVED", reason: `Modified: ${reason}` },
    });
    setModifyTarget(null);
  }

  function handleBatchApproveLow() {
    for (const item of lowRiskItems) {
      decide.mutate({ id: item.id, decision: { decision: "APPROVED" } });
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-40 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Tabs
          defaultValue="ALL"
          onValueChange={(val) => setFilter(val as RiskFilter)}
        >
          <TabsList>
            {RISK_FILTERS.map((level) => (
              <TabsTrigger key={level} value={level}>
                {level}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {lowRiskItems.length > 0 && (
          <Button
            size="sm"
            variant="outline"
            className="text-green-600"
            onClick={handleBatchApproveLow}
          >
            Batch Approve LOW ({lowRiskItems.length})
          </Button>
        )}
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
          <CheckCircle className="size-12 text-green-500" />
          <p className="text-lg font-medium">All caught up</p>
          <p className="text-sm">No pending approvals</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={handleApprove}
              onModify={setModifyTarget}
              onReject={handleReject}
            />
          ))}
        </div>
      )}

      <ModifyDrawer
        approval={modifyTarget}
        open={modifyTarget !== null}
        onSubmit={handleModifySubmit}
        onCancel={() => setModifyTarget(null)}
      />
    </div>
  );
}
