"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AutonomyDial } from "@/components/shared/AutonomyDial";
import { AUTONOMY_LABELS } from "@/types/api";
import type { AutonomyLevel, WorkflowStatus } from "@/types/api";

interface WorkflowAutonomy {
  id: string;
  name: string;
  status: WorkflowStatus;
  autonomyLevel: AutonomyLevel;
}

// Mock data for development
const initialWorkflows: WorkflowAutonomy[] = [
  { id: "wf-1", name: "Customer Onboarding", status: "EXECUTING", autonomyLevel: 2 },
  { id: "wf-2", name: "Invoice Processing", status: "COMPLETE", autonomyLevel: 3 },
  { id: "wf-3", name: "Security Audit", status: "PLANNING", autonomyLevel: 1 },
  { id: "wf-4", name: "Data Migration", status: "AWAITING_APPROVAL", autonomyLevel: 2 },
  { id: "wf-5", name: "Report Generation", status: "EXECUTING", autonomyLevel: 4 },
];

const STATUS_COLORS: Record<WorkflowStatus, string> = {
  PLANNING: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
  EXECUTING: "bg-green-500/10 text-green-700 dark:text-green-400",
  AWAITING_APPROVAL: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400",
  VERIFYING: "bg-purple-500/10 text-purple-700 dark:text-purple-400",
  COMPLETE: "bg-zinc-500/10 text-zinc-500",
  FAILED: "bg-red-500/10 text-red-700 dark:text-red-400",
};

export default function AutonomySettingsPage() {
  const [workflows, setWorkflows] = useState(initialWorkflows);
  const [dirty, setDirty] = useState(false);

  function handleChange(id: string, level: AutonomyLevel) {
    setWorkflows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, autonomyLevel: level } : w))
    );
    setDirty(true);
  }

  function handleSave() {
    // TODO: persist via API
    setDirty(false);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Autonomy Settings
          </h1>
          <p className="text-muted-foreground">
            Set the autonomy level for each workflow to control how
            independently agents can act.
          </p>
        </div>
        <Button onClick={handleSave} disabled={!dirty}>
          Save Changes
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Workflow Autonomy Levels</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Workflow</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Current Level</TableHead>
                <TableHead>Autonomy Dial</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workflows.map((wf) => (
                <TableRow key={wf.id}>
                  <TableCell className="font-medium">{wf.name}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={STATUS_COLORS[wf.status]}
                    >
                      {wf.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {AUTONOMY_LABELS[wf.autonomyLevel]}
                  </TableCell>
                  <TableCell>
                    <AutonomyDial
                      value={wf.autonomyLevel}
                      onChange={(level) => handleChange(wf.id, level)}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
