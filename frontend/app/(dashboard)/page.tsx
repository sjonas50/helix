"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { GitBranch, CheckCircle, Activity, Zap } from "lucide-react";
import { useWorkflows } from "@/lib/api/workflows";
import { useApprovals } from "@/lib/api/approvals";
import type { WorkflowStatus } from "@/types/api";

const STATUS_STYLES: Record<WorkflowStatus, string> = {
  PLANNING: "bg-blue-100 text-blue-700",
  EXECUTING: "bg-yellow-100 text-yellow-700",
  AWAITING_APPROVAL: "bg-orange-100 text-orange-700",
  VERIFYING: "bg-purple-100 text-purple-700",
  COMPLETE: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
};

export default function DashboardPage() {
  const { data: workflows, isLoading: workflowsLoading } = useWorkflows();
  const { data: approvals, isLoading: approvalsLoading } = useApprovals();

  const activeWorkflows = workflows?.filter(
    (w) => w.status === "EXECUTING" || w.status === "AWAITING_APPROVAL" || w.status === "PLANNING"
  ) || [];

  const pendingApprovals = approvals?.filter((a) => a.status === "PENDING") || [];

  const recentWorkflows = workflows?.slice(0, 5) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your Helix AI agent platform.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Active Workflows */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Active Workflows
            </CardTitle>
            <GitBranch className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {workflowsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{activeWorkflows.length}</div>
                <CardDescription>
                  {activeWorkflows.filter((w) => w.status === "EXECUTING").length} executing,{" "}
                  {activeWorkflows.filter((w) => w.status === "AWAITING_APPROVAL").length} awaiting approval
                </CardDescription>
              </>
            )}
          </CardContent>
        </Card>

        {/* Pending Approvals */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Pending Approvals
            </CardTitle>
            <CheckCircle className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {approvalsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{pendingApprovals.length}</div>
                <CardDescription>
                  <Link
                    href="/approvals"
                    className="text-primary underline-offset-4 hover:underline"
                  >
                    Review approvals
                  </Link>
                </CardDescription>
              </>
            )}
          </CardContent>
        </Card>

        {/* Total Workflows */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Total Workflows
            </CardTitle>
            <Activity className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {workflowsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{workflows?.length || 0}</div>
                <CardDescription>All time</CardDescription>
              </>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Quick Actions
            </CardTitle>
            <Zap className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Link href="/workflows">
              <Button variant="default" size="sm" className="w-full">
                New Workflow
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Recent Workflows */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Workflows</CardTitle>
          <CardDescription>
            Latest workflows across your organization.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {workflowsLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : recentWorkflows.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No workflows yet.{" "}
              <Link href="/workflows" className="text-primary underline-offset-4 hover:underline">
                Create your first workflow
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentWorkflows.map((workflow) => (
                <Link
                  key={workflow.id}
                  href={`/workflows/${workflow.id}`}
                  className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      {workflow.name || `Workflow #${workflow.id.slice(0, 8)}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Created {new Date(workflow.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Badge className={STATUS_STYLES[workflow.status] || ""}>
                    {workflow.status}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
