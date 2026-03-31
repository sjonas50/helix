"use client";

import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useWorkflowStore } from "@/lib/store/workflowStore";
import type { Node } from "@xyflow/react";

const nodeTypeLabels: Record<string, string> = {
  trigger: "Trigger",
  action: "Action",
  condition: "Condition",
  approval: "Approval Gate",
  agent: "Agent",
};

interface NodeConfigPanelProps {
  nodes: Node[];
  onSave?: (nodeId: string, data: Record<string, unknown>) => void;
}

export function NodeConfigPanel({ nodes, onSave }: NodeConfigPanelProps) {
  const selectedNodeId = useWorkflowStore((s) => s.selectedNodeId);
  const setSelectedNodeId = useWorkflowStore((s) => s.setSelectedNodeId);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;
  const isOpen = selectedNode !== null;

  const [editData, setEditData] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (selectedNode) {
      setEditData({ ...(selectedNode.data as Record<string, unknown>) });
    }
  }, [selectedNode]);

  const handleFieldChange = (key: string, value: string) => {
    setEditData((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    if (selectedNodeId) {
      onSave?.(selectedNodeId, editData);
      setSelectedNodeId(null);
    }
  };

  const handleCancel = () => {
    setSelectedNodeId(null);
  };

  // Determine editable fields based on node type
  const editableFields = getEditableFields(selectedNode?.type);

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) setSelectedNodeId(null); }}>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>
            {selectedNode ? nodeTypeLabels[selectedNode.type ?? ""] ?? "Node" : "Node"} Configuration
          </SheetTitle>
          <SheetDescription>
            Edit the properties of this node.
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-4 overflow-y-auto px-4 py-2">
          {editableFields.map((field) => (
            <div key={field.key} className="flex flex-col gap-1.5">
              <Label htmlFor={field.key}>{field.label}</Label>
              <Input
                id={field.key}
                value={String(editData[field.key] ?? "")}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                placeholder={field.placeholder}
              />
            </div>
          ))}
          {editableFields.length === 0 && (
            <p className="text-sm text-muted-foreground">No configurable fields for this node type.</p>
          )}
        </div>
        <SheetFooter>
          <Button variant="outline" onClick={handleCancel}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

interface FieldDef {
  key: string;
  label: string;
  placeholder?: string;
}

function getEditableFields(nodeType?: string): FieldDef[] {
  switch (nodeType) {
    case "trigger":
      return [
        { key: "label", label: "Label", placeholder: "Trigger name" },
        { key: "triggerType", label: "Trigger Type", placeholder: "webhook | schedule | manual" },
        { key: "description", label: "Description", placeholder: "What triggers this?" },
      ];
    case "action":
      return [
        { key: "label", label: "Label", placeholder: "Action name" },
        { key: "provider", label: "Integration Provider", placeholder: "e.g. Slack, Jira" },
        { key: "toolName", label: "Tool Name", placeholder: "e.g. send_message" },
        { key: "riskLevel", label: "Risk Level", placeholder: "LOW | MEDIUM | HIGH | CRITICAL" },
      ];
    case "condition":
      return [
        { key: "label", label: "Label", placeholder: "Condition name" },
        { key: "condition", label: "Condition Expression", placeholder: "e.g. status == 'critical'" },
      ];
    case "approval":
      return [
        { key: "label", label: "Label", placeholder: "Approval gate name" },
        { key: "slaMinutes", label: "SLA (minutes)", placeholder: "e.g. 30" },
        { key: "description", label: "Description", placeholder: "What needs approval?" },
      ];
    case "agent":
      return [
        { key: "label", label: "Label", placeholder: "Agent name" },
        { key: "role", label: "Role", placeholder: "researcher | implementer | verifier" },
        { key: "modelName", label: "Model", placeholder: "e.g. claude-sonnet-4-20250514" },
        { key: "description", label: "Description", placeholder: "What does this agent do?" },
      ];
    default:
      return [];
  }
}
