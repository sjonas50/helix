"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Canvas } from "@/components/workflow/Canvas";
import { NodeConfigPanel } from "@/components/workflow/NodeConfigPanel";
import { AutonomyDial } from "@/components/shared/AutonomyDial";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkflow } from "@/lib/api/workflows";
import type { AutonomyLevel } from "@/types/api";
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

export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: workflow, isLoading } = useWorkflow(params.id);
  const [autonomy, setAutonomy] = useState<AutonomyLevel>(2);

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
            Workflow {workflow?.id ? `#${workflow.id.slice(0, 8)}` : ""}
          </h1>
          <div className="mt-1 flex items-center gap-3">
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                workflow?.status === "COMPLETE"
                  ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
                  : workflow?.status === "FAILED"
                    ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                    : "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
              }`}
            >
              {workflow?.status ?? "UNKNOWN"}
            </span>
            {workflow?.created_at && (
              <span className="text-xs text-muted-foreground">
                Created {new Date(workflow.created_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <AutonomyDial value={autonomy} onChange={setAutonomy} />
      </div>

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
