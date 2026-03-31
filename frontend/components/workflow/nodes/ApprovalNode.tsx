"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export type ApprovalNodeData = {
  label: string;
  description?: string;
  slaMinutes?: number;
};

function formatSla(minutes?: number): string {
  if (!minutes) return "No SLA";
  if (minutes < 60) return `${minutes}m SLA`;
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return remaining > 0 ? `${hours}h ${remaining}m SLA` : `${hours}h SLA`;
}

function ApprovalNodeComponent({ data, selected }: NodeProps<Node<ApprovalNodeData>>) {
  return (
    <div
      className={cn(
        "min-w-[200px] rounded-lg border-2 border-orange-500 bg-white px-4 py-3 shadow-md dark:bg-zinc-900",
        selected && "ring-2 ring-orange-400 ring-offset-2"
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-3 !border-2 !border-orange-500 !bg-white dark:!bg-zinc-900"
      />
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300">
          <ShieldCheck className="h-4 w-4" />
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wide text-orange-600 dark:text-orange-400">
            Approval Gate
          </span>
          <span className="text-sm font-semibold text-foreground">
            {data.label || "Requires Approval"}
          </span>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <span className="inline-flex items-center rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-medium text-orange-700 dark:bg-orange-900/40 dark:text-orange-300">
          {formatSla(data.slaMinutes)}
        </span>
        {data.description && (
          <span className="truncate text-xs text-muted-foreground">{data.description}</span>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !border-2 !border-orange-500 !bg-white dark:!bg-zinc-900"
      />
    </div>
  );
}

export const ApprovalNode = memo(ApprovalNodeComponent);
