"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { GitBranch, CheckCircle, Activity, Zap } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your Helix AI agent platform.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Active Workflows */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Active Workflows
            </CardTitle>
            <GitBranch className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <CardDescription>2 executing, 1 awaiting approval</CardDescription>
          </CardContent>
        </Card>

        {/* Pending Approvals */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Pending Approvals
            </CardTitle>
            <CheckCircle className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
            <CardDescription>
              <Link
                href="/approvals"
                className="text-primary underline-offset-4 hover:underline"
              >
                Review approvals
              </Link>
            </CardDescription>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Recent Activity
            </CardTitle>
            <Activity className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">24</div>
            <CardDescription>Events in the last hour</CardDescription>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Quick Actions
            </CardTitle>
            <Zap className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Link href="/workflows">
              <Button variant="default" size="sm" className="w-full">
                Create Workflow
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>
            Latest events across your workflows and agents.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              {
                time: "2 min ago",
                text: "Workflow WF-001 moved to EXECUTING phase",
              },
              {
                time: "5 min ago",
                text: "Approval request created for high-risk action",
              },
              {
                time: "12 min ago",
                text: "Agent researcher-03 completed data collection",
              },
              {
                time: "18 min ago",
                text: "New integration connected: Slack",
              },
              {
                time: "30 min ago",
                text: "Workflow WF-002 completed successfully",
              },
            ].map((event, i) => (
              <div
                key={i}
                className="flex items-start gap-3 text-sm"
              >
                <span className="mt-0.5 size-1.5 shrink-0 rounded-full bg-primary" />
                <div className="flex-1">
                  <p>{event.text}</p>
                  <p className="text-xs text-muted-foreground">{event.time}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
