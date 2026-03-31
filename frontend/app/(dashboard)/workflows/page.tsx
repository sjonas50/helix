"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Sparkles, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

type Category = "All" | "Sales" | "Support" | "Ops" | "HR" | "Finance" | "DevOps";

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: Category;
  integrations: string[];
}

const TEMPLATES: WorkflowTemplate[] = [
  {
    id: "tpl-1",
    name: "Deal-Close Onboarding",
    description: "When a deal closes in CRM, create onboarding project and notify customer success.",
    category: "Sales",
    integrations: ["Salesforce", "Jira", "Slack"],
  },
  {
    id: "tpl-2",
    name: "Critical Ticket Escalation",
    description: "Auto-research customer history on critical tickets and escalate if SLA is at risk.",
    category: "Support",
    integrations: ["Zendesk", "Slack"],
  },
  {
    id: "tpl-3",
    name: "CI/CD Pipeline",
    description: "Run tests on PR merge, deploy to staging, request approval for production.",
    category: "DevOps",
    integrations: ["GitHub", "AWS", "Slack"],
  },
  {
    id: "tpl-4",
    name: "Employee Onboarding",
    description: "Provision accounts across tools when a new hire is added to HRIS.",
    category: "HR",
    integrations: ["BambooHR", "Google Workspace", "Slack"],
  },
  {
    id: "tpl-5",
    name: "Monthly Expense Audit",
    description: "Pull expense reports, flag anomalies, and generate CFO summary.",
    category: "Finance",
    integrations: ["QuickBooks", "Slack"],
  },
  {
    id: "tpl-6",
    name: "Incident Response",
    description: "When PagerDuty fires, gather logs, create Jira ticket, and notify on-call.",
    category: "Ops",
    integrations: ["PagerDuty", "Jira", "Slack", "Datadog"],
  },
];

const CATEGORIES: Category[] = ["All", "Sales", "Support", "Ops", "HR", "Finance", "DevOps"];

const categoryColors: Record<string, string> = {
  Sales: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  Support: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  Ops: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
  HR: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  Finance: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  DevOps: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300",
};

export default function WorkflowsPage() {
  const router = useRouter();
  const [activeCategory, setActiveCategory] = useState<Category>("All");

  const filtered =
    activeCategory === "All"
      ? TEMPLATES
      : TEMPLATES.filter((t) => t.category === activeCategory);

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Workflows</h1>
          <p className="text-sm text-muted-foreground">
            Start from a template or describe what you want to automate.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.push("/workflows/new")}>
            <Sparkles className="mr-1 h-4 w-4" />
            Create from Description
          </Button>
          <Button onClick={() => router.push("/workflows/new")}>
            <Plus className="mr-1 h-4 w-4" />
            Create from Scratch
          </Button>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setActiveCategory(cat)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeCategory === cat
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((template) => (
          <Card key={template.id} className="cursor-pointer transition-shadow hover:shadow-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{template.name}</CardTitle>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    categoryColors[template.category] ?? "bg-muted text-muted-foreground"
                  }`}
                >
                  {template.category}
                </span>
              </div>
              <CardDescription>{template.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-1">
                {template.integrations.map((integration) => (
                  <span
                    key={integration}
                    className="rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                  >
                    {integration}
                  </span>
                ))}
              </div>
            </CardContent>
            <CardFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push(`/workflows/new?template=${template.id}`)}
              >
                Use Template
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  );
}
