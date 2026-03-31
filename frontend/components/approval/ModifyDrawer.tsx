"use client";

import { useState } from "react";
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
import type { ApprovalRequest } from "@/types/api";

interface ModifyDrawerProps {
  approval: ApprovalRequest | null;
  open: boolean;
  onSubmit: (id: string, reason: string) => void;
  onCancel: () => void;
}

export function ModifyDrawer({
  approval,
  open,
  onSubmit,
  onCancel,
}: ModifyDrawerProps) {
  const [reason, setReason] = useState("");

  if (!approval) return null;

  function handleSubmit() {
    if (!approval) return;
    onSubmit(approval.id, reason);
    setReason("");
  }

  return (
    <Sheet open={open} onOpenChange={(val) => !val && onCancel()}>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Modify Approval</SheetTitle>
          <SheetDescription>
            Adjust parameters before approving this action.
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-4 p-4">
          <div className="space-y-2">
            <Label>Action</Label>
            <Input value={approval.action_description} disabled />
          </div>

          <div className="space-y-2">
            <Label>Risk Level</Label>
            <Input value={approval.risk_level} disabled />
          </div>

          <div className="space-y-2">
            <Label>Workflow ID</Label>
            <Input value={approval.workflow_id} disabled />
          </div>

          <div className="space-y-2">
            <Label htmlFor="modify-reason">Modification Reason</Label>
            <Input
              id="modify-reason"
              placeholder="Describe the modifications..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
        </div>

        <SheetFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            className="bg-amber-500 text-white hover:bg-amber-600"
            onClick={handleSubmit}
          >
            Approve with Modifications
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
