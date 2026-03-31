"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Undo2 } from "lucide-react";
import type { AuditEvent } from "@/types/api";
import Link from "next/link";

const EVENT_DESCRIPTIONS: Record<string, string> = {
  "workflow.created": "Created workflow",
  "workflow.started": "Started workflow",
  "workflow.completed": "Completed workflow",
  "workflow.failed": "Workflow failed",
  "agent.spawned": "Spawned agent",
  "agent.terminated": "Terminated agent",
  "approval.requested": "Requested approval",
  "approval.approved": "Approved request",
  "approval.rejected": "Rejected request",
  "approval.escalated": "Escalated approval",
  "integration.connected": "Connected integration",
  "integration.disconnected": "Disconnected integration",
  "memory.created": "Created memory record",
  "memory.updated": "Updated memory record",
  "memory.deleted": "Deleted memory record",
  "settings.updated": "Updated settings",
};

function describeEvent(event: AuditEvent): string {
  return EVENT_DESCRIPTIONS[event.event_type] ?? event.event_type;
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function resourceLink(event: AuditEvent): string | null {
  if (!event.resource_type || !event.resource_id) return null;
  const routes: Record<string, string> = {
    workflow: "/workflows",
    integration: "/integrations",
    approval: "/approvals",
  };
  const base = routes[event.resource_type];
  if (!base) return null;
  return `${base}/${event.resource_id}`;
}

interface AuditEntryProps {
  event: AuditEvent;
  onUndo?: (eventId: string) => void;
}

export function AuditEntry({ event, onUndo }: AuditEntryProps) {
  const link = resourceLink(event);
  const isReversible =
    event.event_type.includes("created") ||
    event.event_type.includes("updated") ||
    event.event_type.includes("connected");

  return (
    <div
      className="flex items-center gap-4 py-2 text-sm"
      data-testid="audit-entry"
    >
      <span className="w-20 shrink-0 text-xs text-muted-foreground">
        {relativeTime(event.created_at)}
      </span>

      <span className="flex-1" data-testid="event-description">
        {describeEvent(event)}
      </span>

      <Badge variant={event.agent_id ? "secondary" : "outline"}>
        {event.agent_id ? "Agent" : "User"}
      </Badge>

      {link ? (
        <Link
          href={link}
          className="text-xs text-primary underline-offset-4 hover:underline"
        >
          {event.resource_type}
        </Link>
      ) : (
        <span className="w-20" />
      )}

      {isReversible && onUndo && (
        <Button
          size="icon-xs"
          variant="ghost"
          onClick={() => onUndo(event.id)}
          title="Undo action"
        >
          <Undo2 className="size-3" />
        </Button>
      )}
    </div>
  );
}
