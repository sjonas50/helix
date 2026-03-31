"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentRole } from "@/types/api";

export type AgentNodeData = {
  label: string;
  role: AgentRole;
  modelName: string;
  description?: string;
};

const roleLabels: Record<AgentRole, string> = {
  coordinator: "Coordinator",
  researcher: "Researcher",
  implementer: "Implementer",
  verifier: "Verifier",
};

function AgentNodeComponent({ data, selected }: NodeProps<Node<AgentNodeData>>) {
  return (
    <div
      className={cn(
        "min-w-[200px] rounded-lg border-2 border-purple-500 bg-white px-4 py-3 shadow-md dark:bg-zinc-900",
        selected && "ring-2 ring-purple-400 ring-offset-2"
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-3 !border-2 !border-purple-500 !bg-white dark:!bg-zinc-900"
      />
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300">
          <Bot className="h-4 w-4" />
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wide text-purple-600 dark:text-purple-400">
            Agent
          </span>
          <span className="text-sm font-semibold text-foreground">
            {data.label || roleLabels[data.role]}
          </span>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
          {roleLabels[data.role]}
        </span>
        <span className="text-xs text-muted-foreground">{data.modelName}</span>
      </div>
      {data.description && (
        <p className="mt-1.5 text-xs text-muted-foreground">{data.description}</p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !border-2 !border-purple-500 !bg-white dark:!bg-zinc-900"
      />
    </div>
  );
}

export const AgentNode = memo(AgentNodeComponent);
