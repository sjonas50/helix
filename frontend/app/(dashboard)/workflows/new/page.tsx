"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { NLCreator } from "@/components/workflow/NLCreator";
import { Canvas } from "@/components/workflow/Canvas";
import { NodeConfigPanel } from "@/components/workflow/NodeConfigPanel";
import { useWorkflowStore } from "@/lib/store/workflowStore";

// Template descriptions — when user clicks "Use Template", we pre-fill the NL input
// and auto-generate via the real backend endpoint
const TEMPLATE_DESCRIPTIONS: Record<string, string> = {
  "tpl-1": "When a deal closes in Salesforce, create an onboarding project in Jira with the account details, and notify the customer success team in Slack with a summary.",
  "tpl-2": "When a critical support ticket is created in Zendesk, research the customer's history in Salesforce, draft a response, and escalate in Slack if the SLA deadline is within 2 hours.",
  "tpl-3": "When a GitHub PR is merged to main, create a Jira ticket to track the deployment, notify the team in Slack, and verify the deploy completed successfully.",
  "tpl-4": "When a new employee is added, invite them to the relevant Slack channels, create their Jira account, and add them to the GitHub organization.",
  "tpl-5": "Every month-end, pull opportunity data from Salesforce, create a revenue summary document in Google Docs, and post the highlights to the finance Slack channel.",
  "tpl-6": "When a ServiceNow incident is created with priority 1, gather context from Jira and Slack, create a war room Slack channel, and generate a post-incident review document in Google Docs.",
};

function NewWorkflowContent() {
  const [activeTab, setActiveTab] = useState<string>("describe");
  const generatedNodes = useWorkflowStore((s) => s.generatedNodes);
  const generatedEdges = useWorkflowStore((s) => s.generatedEdges);
  const setNlInput = useWorkflowStore((s) => s.setNlInput);

  const searchParams = useSearchParams();
  const templateId = searchParams.get("template");

  // Pre-fill NL input from template
  useEffect(() => {
    if (templateId && TEMPLATE_DESCRIPTIONS[templateId]) {
      setNlInput(TEMPLATE_DESCRIPTIONS[templateId]);
    }
  }, [templateId, setNlInput]);

  const handlePreviewCanvas = () => {
    setActiveTab("build");
  };

  return (
    <div className="flex flex-col gap-4 p-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">New Workflow</h1>
        <p className="text-sm text-muted-foreground">
          {templateId
            ? "Template loaded — click Generate to build the workflow, or edit the description first."
            : "Describe what you want to automate or build visually on the canvas."}
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="describe">Describe</TabsTrigger>
          <TabsTrigger value="build">Build</TabsTrigger>
        </TabsList>

        <TabsContent value="describe">
          <div className="py-6">
            <NLCreator onPreviewCanvas={handlePreviewCanvas} />
          </div>
        </TabsContent>

        <TabsContent value="build">
          <div className="flex flex-col gap-4 py-4">
            <Canvas
              initialNodes={generatedNodes}
              initialEdges={generatedEdges}
              className="h-[calc(100vh-280px)] w-full rounded-lg border bg-zinc-50 dark:bg-zinc-950"
            />
            <NodeConfigPanel
              nodes={generatedNodes}
              onSave={(nodeId, data) => {
                console.log("Save node", nodeId, data);
              }}
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function NewWorkflowPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading...</div>}>
      <NewWorkflowContent />
    </Suspense>
  );
}
