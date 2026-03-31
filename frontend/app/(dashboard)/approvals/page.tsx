"use client";

import { useMemo } from "react";
import { useApprovals } from "@/lib/api/approvals";
import { ApprovalQueue } from "@/components/approval/ApprovalQueue";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CircleAlert,
} from "lucide-react";
import type { RiskLevel } from "@/types/api";

const RISK_ICONS: Record<RiskLevel, React.ReactNode> = {
  LOW: <ShieldCheck className="size-4 text-green-500" />,
  MEDIUM: <AlertTriangle className="size-4 text-yellow-500" />,
  HIGH: <CircleAlert className="size-4 text-orange-500" />,
  CRITICAL: <ShieldAlert className="size-4 text-red-500" />,
};

export default function ApprovalsPage() {
  const { data: approvals } = useApprovals();

  const stats = useMemo(() => {
    const pending = (approvals ?? []).filter((a) => a.status === "PENDING");
    const byRisk: Record<RiskLevel, number> = {
      LOW: 0,
      MEDIUM: 0,
      HIGH: 0,
      CRITICAL: 0,
    };
    for (const a of pending) {
      byRisk[a.risk_level]++;
    }
    return { total: pending.length, byRisk };
  }, [approvals]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Approvals</h1>
        <p className="text-muted-foreground">
          Review and manage pending approval requests.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Total Pending
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>

        {(Object.keys(stats.byRisk) as RiskLevel[]).map((level) => (
          <Card key={level}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">{level}</CardTitle>
              {RISK_ICONS[level]}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.byRisk[level]}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <ApprovalQueue />
    </div>
  );
}
