"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Play, Loader2, AlertTriangle, CheckCircle2, XCircle, Clock } from "lucide-react";
import { Canvas } from "@/components/workflow/Canvas";
import { NodeConfigPanel } from "@/components/workflow/NodeConfigPanel";
import { AutonomyDial } from "@/components/shared/AutonomyDial";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useWorkflow, useRunWorkflow } from "@/lib/api/workflows";
import type { AutonomyLevel, WorkflowStatus } from "@/types/api";
import type { Node, Edge } from "@xyflow/react";

/** Demo nodes for display when workflow data loads. Replace with real graph from API. */
const DEMO_NODES: Node[] = [
  { id: "t1", type: "trigger", position: { x: 0, y: 0 }, data: { label: "Webhook Trigger", triggerType: "webhook", description: "Incoming event" } },
  { id: "a1", type: "agent", position: { x: 0, y: 0 }, data: { label: "Researcher", role: "researcher", modelName: "claude-sonnet-4-20250514" } },
  { id: "act1", type: "action", position: { x: 0, y: 0 }, data: { label: "Send Notification", provider: "Slack", toolName: "send_message", riskLevel: "LOW" } },
];

const DEMO_EDGES: Edge[] = [
  { id: "e1", source: "t1", target: "a1" },
  { id: "e2", source: "a1", target: "act1" },
];

const STATUS_STYLES: Record<WorkflowStatus, string> = {
  PLANNING: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  EXECUTING: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  AWAITING_APPROVAL: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
  VERIFYING: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  COMPLETE: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  FAILED: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
};

export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: workflow, isLoading } = useWorkflow(params.id);
  const [autonomy, setAutonomy] = useState<AutonomyLevel>(2);
  const runMutation = useRunWorkflow();

  const handleRun = () => {
    runMutation.mutate(params.id);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[500px] w-full rounded-lg" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {workflow?.name || `Workflow #${workflow?.id?.slice(0, 8) || ""}`}
          </h1>
          {workflow?.description && (
            <p className="mt-1 text-sm text-muted-foreground">{workflow.description}</p>
          )}
          <div className="mt-2 flex items-center gap-3">
            <Badge className={STATUS_STYLES[workflow?.status as WorkflowStatus] || ""}>
              {workflow?.status ?? "UNKNOWN"}
            </Badge>
            {workflow?.created_at && (
              <span className="text-xs text-muted-foreground">
                Created {new Date(workflow.created_at).toLocaleDateString()}
              </span>
            )}
            {workflow?.completed_at && (
              <span className="text-xs text-muted-foreground">
                Completed {new Date(workflow.completed_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          {workflow?.status === "PLANNING" && (
            <Button onClick={handleRun} disabled={runMutation.isPending}>
              {runMutation.isPending ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-1 h-4 w-4" />
              )}
              Run Workflow
            </Button>
          )}
          <AutonomyDial value={autonomy} onChange={setAutonomy} />
        </div>
      </div>

      {/* Status banners */}
      {workflow?.status === "AWAITING_APPROVAL" && (
        <div className="flex items-center gap-3 rounded-lg border border-orange-200 bg-orange-50 p-4 dark:border-orange-800 dark:bg-orange-950">
          <AlertTriangle className="h-5 w-5 text-orange-600" />
          <div className="flex-1">
            <p className="text-sm font-medium text-orange-800 dark:text-orange-200">
              This workflow is awaiting approval before it can continue.
            </p>
          </div>
          <Link href="/approvals">
            <Button variant="outline" size="sm">
              Review Approvals
            </Button>
          </Link>
        </div>
      )}

      {workflow?.status === "EXECUTING" && (
        <div className="flex items-center gap-3 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-950">
          <Loader2 className="h-5 w-5 animate-spin text-yellow-600" />
          <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
            Workflow is currently executing...
          </p>
        </div>
      )}

      {workflow?.status === "COMPLETE" && (
        <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950">
          <CheckCircle2 className="h-5 w-5 text-green-600" />
          <p className="text-sm font-medium text-green-800 dark:text-green-200">
            Workflow completed successfully
            {workflow.completed_at && ` at ${new Date(workflow.completed_at).toLocaleString()}`}
          </p>
        </div>
      )}

      {workflow?.status === "FAILED" && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950">
          <XCircle className="h-5 w-5 text-red-600" />
          <p className="text-sm font-medium text-red-800 dark:text-red-200">
            Workflow failed
            {workflow.updated_at && ` at ${new Date(workflow.updated_at).toLocaleString()}`}
          </p>
        </div>
      )}

      {runMutation.isSuccess && (
        <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <Clock className="h-5 w-5 text-blue-600" />
          <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
            Workflow run dispatched. Status will update via WebSocket.
          </p>
        </div>
      )}

      {/* Canvas */}
      <Canvas
        initialNodes={DEMO_NODES}
        initialEdges={DEMO_EDGES}
        className="h-[500px] w-full rounded-lg border bg-zinc-50 dark:bg-zinc-950"
      />

      <NodeConfigPanel
        nodes={DEMO_NODES}
        onSave={(nodeId, data) => {
          console.log("Save node", nodeId, data);
        }}
      />

      {/* Run History placeholder */}
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-foreground">Run History</h2>
        <div className="rounded-lg border bg-muted/20 p-8 text-center text-sm text-muted-foreground">
          No runs yet. Execute the workflow to see history here.
        </div>
      </div>
    </div>
  );
}
