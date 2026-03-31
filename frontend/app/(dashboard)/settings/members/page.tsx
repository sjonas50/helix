"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { UserPlus } from "lucide-react";

type Role = "admin" | "operator" | "viewer" | "auditor";

interface Member {
  id: string;
  name: string;
  email: string;
  role: Role;
  lastActive: string;
}

const ROLE_COLORS: Record<Role, string> = {
  admin: "bg-red-500/10 text-red-700 dark:text-red-400",
  operator: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
  viewer: "bg-zinc-500/10 text-zinc-500",
  auditor: "bg-purple-500/10 text-purple-700 dark:text-purple-400",
};

// Mock data for development
const initialMembers: Member[] = [
  { id: "u-1", name: "Sarah Chen", email: "sarah@acme.com", role: "admin", lastActive: "2026-03-31T10:30:00Z" },
  { id: "u-2", name: "James Wilson", email: "james@acme.com", role: "operator", lastActive: "2026-03-31T09:15:00Z" },
  { id: "u-3", name: "Maria Garcia", email: "maria@acme.com", role: "viewer", lastActive: "2026-03-30T16:45:00Z" },
  { id: "u-4", name: "Alex Kim", email: "alex@acme.com", role: "auditor", lastActive: "2026-03-29T14:20:00Z" },
];

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function MembersPage() {
  const [members, setMembers] = useState(initialMembers);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("viewer");

  function handleRoleChange(id: string, role: Role) {
    setMembers((prev) =>
      prev.map((m) => (m.id === id ? { ...m, role } : m))
    );
  }

  function handleInvite() {
    if (!inviteEmail.trim()) return;
    const newMember: Member = {
      id: `u-${Date.now()}`,
      name: inviteEmail.split("@")[0],
      email: inviteEmail,
      role: inviteRole,
      lastActive: new Date().toISOString(),
    };
    setMembers((prev) => [...prev, newMember]);
    setInviteEmail("");
    setInviteRole("viewer");
    setInviteOpen(false);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Members</h1>
          <p className="text-muted-foreground">
            Manage team members and their roles for access control.
          </p>
        </div>

        <Button onClick={() => setInviteOpen(true)}>
          <UserPlus className="mr-2 size-4" />
          Invite Member
        </Button>
        <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite a Team Member</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-2">
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  placeholder="colleague@company.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-role">Role</Label>
                <Select
                  value={inviteRole}
                  onValueChange={(v) => setInviteRole(v as Role)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="operator">Operator</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                    <SelectItem value="auditor">Auditor</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={handleInvite} className="w-full">
                Send Invitation
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Last Active</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.map((member) => (
                <TableRow key={member.id}>
                  <TableCell className="font-medium">{member.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {member.email}
                  </TableCell>
                  <TableCell>
                    <Select
                      value={member.role}
                      onValueChange={(v) =>
                        handleRoleChange(member.id, v as Role)
                      }
                    >
                      <SelectTrigger className="w-32">
                        <Badge
                          variant="outline"
                          className={ROLE_COLORS[member.role]}
                        >
                          {member.role}
                        </Badge>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="operator">Operator</SelectItem>
                        <SelectItem value="viewer">Viewer</SelectItem>
                        <SelectItem value="auditor">Auditor</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {relativeTime(member.lastActive)}
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
