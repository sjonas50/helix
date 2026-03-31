"use client";

import { cn } from "@/lib/utils";
import type { AutonomyLevel } from "@/types/api";
import { AUTONOMY_LABELS } from "@/types/api";

const positions: { level: AutonomyLevel; color: string; activeColor: string }[] = [
  { level: 1, color: "bg-zinc-200 dark:bg-zinc-700", activeColor: "bg-zinc-500 dark:bg-zinc-400" },
  { level: 2, color: "bg-blue-200 dark:bg-blue-900", activeColor: "bg-blue-500 dark:bg-blue-400" },
  { level: 3, color: "bg-amber-200 dark:bg-amber-900", activeColor: "bg-amber-500 dark:bg-amber-400" },
  { level: 4, color: "bg-green-200 dark:bg-green-900", activeColor: "bg-green-500 dark:bg-green-400" },
];

interface AutonomyDialProps {
  value: AutonomyLevel;
  onChange: (level: AutonomyLevel) => void;
  className?: string;
}

export function AutonomyDial({ value, onChange, className }: AutonomyDialProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Autonomy Level
      </span>
      <div className="inline-flex rounded-lg border bg-muted/30 p-1" role="radiogroup" aria-label="Autonomy level">
        {positions.map((pos) => {
          const isActive = pos.level === value;
          return (
            <button
              key={pos.level}
              type="button"
              role="radio"
              aria-checked={isActive}
              aria-label={AUTONOMY_LABELS[pos.level]}
              onClick={() => onChange(pos.level)}
              className={cn(
                "relative rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                isActive
                  ? cn(pos.activeColor, "text-white shadow-sm")
                  : cn("text-muted-foreground hover:bg-muted hover:text-foreground")
              )}
            >
              {pos.level}
            </button>
          );
        })}
      </div>
      <span className="text-sm font-medium text-foreground">
        {AUTONOMY_LABELS[value]}
      </span>
    </div>
  );
}
