"use client";

import { useState, useMemo } from "react";
import { useAuditLog, useUndoAction } from "@/lib/api/audit";
import { apiClient } from "@/lib/api/client";
import { AuditEntry } from "@/components/shared/AuditEntry";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ShieldCheck, ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 20;

const EVENT_TYPE_OPTIONS = [
  "workflow.created",
  "workflow.started",
  "workflow.completed",
  "workflow.failed",
  "agent.spawned",
  "agent.terminated",
  "approval.requested",
  "approval.approved",
  "approval.rejected",
  "integration.connected",
  "integration.disconnected",
  "memory.created",
  "memory.updated",
  "memory.deleted",
  "settings.updated",
];

const RESOURCE_TYPE_OPTIONS = [
  "workflow",
  "agent",
  "approval",
  "integration",
  "memory",
];

export default function AuditPage() {
  const [offset, setOffset] = useState(0);
  const [eventType, setEventType] = useState<string>("");
  const [resourceType, setResourceType] = useState<string>("");
  const [verifying, setVerifying] = useState(false);
  const [integrityResult, setIntegrityResult] = useState<string | null>(null);

  const params = useMemo(
    () => ({
      limit: PAGE_SIZE,
      offset,
      ...(eventType ? { event_type: eventType } : {}),
      ...(resourceType ? { resource_type: resourceType } : {}),
    }),
    [offset, eventType, resourceType]
  );

  const { data, isLoading } = useAuditLog(params);
  const undo = useUndoAction();

  const events = data?.events ?? [];
  const total = data?.total ?? 0;
  const hasNext = offset + PAGE_SIZE < total;
  const hasPrev = offset > 0;

  async function handleVerifyIntegrity() {
    setVerifying(true);
    setIntegrityResult(null);
    try {
      const result = await apiClient<{ valid: boolean; message: string }>(
        "/audit/integrity"
      );
      setIntegrityResult(
        result.valid ? "Integrity verified" : `Issue: ${result.message}`
      );
    } catch {
      setIntegrityResult("Verification failed");
    } finally {
      setVerifying(false);
    }
  }

  function handleUndo(eventId: string) {
    undo.mutate(eventId);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Audit Trail</h1>
        <p className="text-muted-foreground">
          Complete history of all actions across your organization.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={eventType}
          onValueChange={(val: string | null) => {
            setEventType(val ?? "");
            setOffset(0);
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Event type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All events</SelectItem>
            {EVENT_TYPE_OPTIONS.map((t) => (
              <SelectItem key={t} value={t}>
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={resourceType}
          onValueChange={(val: string | null) => {
            setResourceType(val ?? "");
            setOffset(0);
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Resource type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All resources</SelectItem>
            {RESOURCE_TYPE_OPTIONS.map((t) => (
              <SelectItem key={t} value={t}>
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="ml-auto flex items-center gap-2">
          {integrityResult && (
            <Badge
              variant={
                integrityResult.includes("verified")
                  ? "secondary"
                  : "destructive"
              }
            >
              {integrityResult}
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleVerifyIntegrity}
            disabled={verifying}
          >
            <ShieldCheck className="mr-1 size-4" />
            {verifying ? "Verifying..." : "Verify Integrity"}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Event</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                  No audit events found.
                </TableCell>
              </TableRow>
            ) : (
              events.map((event) => (
                <TableRow key={event.id}>
                  <TableCell colSpan={5} className="p-0">
                    <AuditEntry event={event} onUndo={handleUndo} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      )}

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Showing {events.length > 0 ? offset + 1 : 0}–
          {Math.min(offset + PAGE_SIZE, total)} of {total}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon-sm"
            disabled={!hasPrev}
            onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
          >
            <ChevronLeft className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            disabled={!hasNext}
            onClick={() => setOffset((o) => o + PAGE_SIZE)}
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
