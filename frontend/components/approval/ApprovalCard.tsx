"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Clock } from "lucide-react";
import type { ApprovalRequest, RiskLevel } from "@/types/api";

const RISK_COLORS: Record<RiskLevel, string> = {
  LOW: "bg-green-500/15 text-green-700 dark:text-green-400",
  MEDIUM: "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400",
  HIGH: "bg-orange-500/15 text-orange-700 dark:text-orange-400",
  CRITICAL: "bg-red-500/15 text-red-700 dark:text-red-400",
};

function formatTimeRemaining(deadline: string | null): string {
  if (!deadline) return "No deadline";
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff <= 0) return "Expired";
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  return `${hours}h ${minutes}m`;
}

interface ApprovalCardProps {
  approval: ApprovalRequest;
  onApprove: (id: string) => void;
  onModify: (approval: ApprovalRequest) => void;
  onReject: (id: string) => void;
}

export function ApprovalCard({
  approval,
  onApprove,
  onModify,
  onReject,
}: ApprovalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [timeLeft, setTimeLeft] = useState(() =>
    formatTimeRemaining(approval.sla_deadline)
  );

  useEffect(() => {
    if (!approval.sla_deadline) return;
    const interval = setInterval(() => {
      setTimeLeft(formatTimeRemaining(approval.sla_deadline));
    }, 60_000);
    return () => clearInterval(interval);
  }, [approval.sla_deadline]);

  const isExpired = timeLeft === "Expired";

  return (
    <Card data-testid="approval-card">
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div className="space-y-1">
          <CardTitle className="text-base font-bold">
            {approval.action_description}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge
              data-testid="risk-badge"
              className={RISK_COLORS[approval.risk_level]}
            >
              {approval.risk_level}
            </Badge>
            <span
              className={`flex items-center gap-1 text-xs ${
                isExpired ? "text-red-500" : "text-muted-foreground"
              }`}
            >
              <Clock className="size-3" />
              {timeLeft}
            </span>
          </div>
        </div>
      </CardHeader>

      {approval.decision_reason && (
        <CardContent className="pt-0">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Why: </span>
            {approval.decision_reason}
          </p>
        </CardContent>
      )}

      {expanded && (
        <CardContent className="pt-0">
          <div className="rounded-md bg-muted p-3 text-xs font-mono">
            <p className="text-muted-foreground">
              Workflow: {approval.workflow_id}
            </p>
            <p className="text-muted-foreground">
              Created: {new Date(approval.created_at).toLocaleString()}
            </p>
            <p className="text-muted-foreground">Status: {approval.status}</p>
          </div>
        </CardContent>
      )}

      <CardContent className="pt-0">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="size-3" /> Hide details
            </>
          ) : (
            <>
              <ChevronDown className="size-3" /> Show details
            </>
          )}
        </button>
      </CardContent>

      <CardFooter className="gap-2">
        <Button
          size="sm"
          className="bg-green-600 text-white hover:bg-green-700"
          onClick={() => onApprove(approval.id)}
          data-testid="approve-btn"
        >
          Approve
        </Button>
        <Button
          size="sm"
          className="bg-amber-500 text-white hover:bg-amber-600"
          onClick={() => onModify(approval)}
          data-testid="modify-btn"
        >
          Modify
        </Button>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => onReject(approval.id)}
          data-testid="reject-btn"
        >
          Reject
        </Button>
      </CardFooter>
    </Card>
  );
}
