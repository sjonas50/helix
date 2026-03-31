"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/types/api";

export type ActionNodeData = {
  label: string;
  provider: string;
  toolName: string;
  riskLevel: RiskLevel;
  description?: string;
};

const riskColors: Record<RiskLevel, { bg: string; text: string; border: string }> = {
  LOW: { bg: "bg-green-100 dark:bg-green-900/40", text: "text-green-700 dark:text-green-300", border: "border-green-400" },
  MEDIUM: { bg: "bg-yellow-100 dark:bg-yellow-900/40", text: "text-yellow-700 dark:text-yellow-300", border: "border-yellow-400" },
  HIGH: { bg: "bg-orange-100 dark:bg-orange-900/40", text: "text-orange-700 dark:text-orange-300", border: "border-orange-400" },
  CRITICAL: { bg: "bg-red-100 dark:bg-red-900/40", text: "text-red-700 dark:text-red-300", border: "border-red-400" },
};

function ActionNodeComponent({ data, selected }: NodeProps<Node<ActionNodeData>>) {
  const risk = riskColors[data.riskLevel] ?? riskColors.LOW;

  return (
    <div
      className={cn(
        "min-w-[200px] rounded-lg border bg-white px-4 py-3 shadow-md dark:bg-zinc-900",
        "border-slate-300 dark:border-slate-700",
        selected && "ring-2 ring-blue-400 ring-offset-2"
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-3 !border-2 !border-slate-400 !bg-white dark:!bg-zinc-900"
      />
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
          <Zap className="h-4 w-4" />
        </div>
        <div className="flex flex-col">
          <span className="text-xs text-muted-foreground">{data.provider}</span>
          <span className="text-sm font-semibold text-foreground">{data.toolName}</span>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
            risk.bg,
            risk.text
          )}
        >
          {data.riskLevel}
        </span>
        {data.description && (
          <span className="truncate text-xs text-muted-foreground">{data.description}</span>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !border-2 !border-slate-400 !bg-white dark:!bg-zinc-900"
      />
    </div>
  );
}

export const ActionNode = memo(ActionNodeComponent);
