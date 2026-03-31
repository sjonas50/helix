"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { Webhook, Clock, MousePointerClick } from "lucide-react";
import { cn } from "@/lib/utils";

export type TriggerType = "webhook" | "schedule" | "manual";

export type TriggerNodeData = {
  label: string;
  triggerType: TriggerType;
  description?: string;
};

const triggerIcons: Record<TriggerType, React.ElementType> = {
  webhook: Webhook,
  schedule: Clock,
  manual: MousePointerClick,
};

const triggerLabels: Record<TriggerType, string> = {
  webhook: "Webhook",
  schedule: "Schedule",
  manual: "Manual",
};

function TriggerNodeComponent({ data, selected }: NodeProps<Node<TriggerNodeData>>) {
  const Icon = triggerIcons[data.triggerType] ?? Webhook;

  return (
    <div
      className={cn(
        "min-w-[180px] rounded-lg border-2 border-green-500 bg-white px-4 py-3 shadow-md dark:bg-zinc-900",
        selected && "ring-2 ring-green-400 ring-offset-2"
      )}
    >
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wide text-green-600 dark:text-green-400">
            Trigger
          </span>
          <span className="text-sm font-semibold text-foreground">
            {data.label || triggerLabels[data.triggerType]}
          </span>
        </div>
      </div>
      {data.description && (
        <p className="mt-2 text-xs text-muted-foreground">{data.description}</p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !border-2 !border-green-500 !bg-white dark:!bg-zinc-900"
      />
    </div>
  );
}

export const TriggerNode = memo(TriggerNodeComponent);
