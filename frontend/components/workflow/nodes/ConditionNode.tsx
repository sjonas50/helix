"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

export type ConditionNodeData = {
  label: string;
  condition: string;
};

function ConditionNodeComponent({ data, selected }: NodeProps<Node<ConditionNodeData>>) {
  return (
    <div
      className={cn(
        "relative min-w-[160px]",
        selected && "[&>.diamond]:ring-2 [&>.diamond]:ring-amber-400 [&>.diamond]:ring-offset-2"
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-3 !border-2 !border-amber-500 !bg-white dark:!bg-zinc-900"
      />
      <div className="diamond rotate-45 rounded-lg border-2 border-amber-500 bg-white p-1 shadow-md dark:bg-zinc-900">
        <div className="-rotate-45 flex flex-col items-center px-4 py-3">
          <GitBranch className="mb-1 h-4 w-4 text-amber-600 dark:text-amber-400" />
          <span className="text-xs font-semibold text-foreground">{data.label || "Condition"}</span>
          <span className="mt-0.5 max-w-[120px] text-center text-[10px] leading-tight text-muted-foreground">
            {data.condition}
          </span>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        id="true"
        style={{ left: "30%" }}
        className="!h-3 !w-3 !border-2 !border-green-500 !bg-white dark:!bg-zinc-900"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="false"
        style={{ left: "70%" }}
        className="!h-3 !w-3 !border-2 !border-red-500 !bg-white dark:!bg-zinc-900"
      />
      <span className="absolute bottom-[-18px] left-[22%] text-[9px] font-medium text-green-600">
        True
      </span>
      <span className="absolute bottom-[-18px] left-[63%] text-[9px] font-medium text-red-600">
        False
      </span>
    </div>
  );
}

export const ConditionNode = memo(ConditionNodeComponent);
