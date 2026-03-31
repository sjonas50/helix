"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AccessLevel, MemoryRecord } from "@/types/api";

const ACCESS_COLORS: Record<AccessLevel, string> = {
  PUBLIC: "bg-green-500/10 text-green-700 dark:text-green-400",
  ROLE_RESTRICTED: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400",
  CONFIDENTIAL: "bg-red-500/10 text-red-700 dark:text-red-400",
};

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface MemoryCardProps {
  memory: MemoryRecord;
}

export function MemoryCard({ memory }: MemoryCardProps) {
  const truncated =
    memory.content.length > 200
      ? memory.content.slice(0, 200) + "..."
      : memory.content;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base font-bold" data-testid="memory-topic">
            {memory.topic}
          </CardTitle>
          <Badge
            variant="outline"
            className={ACCESS_COLORS[memory.access_level]}
            data-testid="access-badge"
          >
            {memory.access_level}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground" data-testid="memory-content">
          {truncated}
        </p>

        <div className="flex flex-wrap items-center gap-2">
          {memory.tags?.map((tag) => (
            <Badge key={tag} variant="secondary" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>v{memory.version}</span>
          <span>{relativeTime(memory.created_at)}</span>
          {memory.similarity !== undefined && (
            <span>{(memory.similarity * 100).toFixed(0)}% match</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
