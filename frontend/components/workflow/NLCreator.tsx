"use client";

import { useState, useCallback } from "react";
import { Loader2, Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWorkflowStore } from "@/lib/store/workflowStore";

const EXAMPLE_PROMPTS = [
  { category: "Sales", text: "When a deal closes in Salesforce, create an onboarding project in Jira and notify the CS team in Slack" },
  { category: "Support", text: "When a critical support ticket is created, research the customer history, draft a response, and escalate if SLA is breached" },
  { category: "DevOps", text: "When a GitHub PR is merged to main, run tests, deploy to staging, and request approval before production deploy" },
  { category: "HR", text: "When a new employee is added to BambooHR, create accounts in Google Workspace, Slack, and schedule orientation meetings" },
  { category: "Finance", text: "Every month-end, pull expense reports from QuickBooks, flag anomalies, and generate a summary for the CFO" },
];

interface NLCreatorProps {
  onPreviewCanvas?: () => void;
}

export function NLCreator({ onPreviewCanvas }: NLCreatorProps) {
  const nlInput = useWorkflowStore((s) => s.nlInput);
  const setNlInput = useWorkflowStore((s) => s.setNlInput);
  const setGeneratedGraph = useWorkflowStore((s) => s.setGeneratedGraph);

  const [loading, setLoading] = useState(false);
  const [generatedDescription, setGeneratedDescription] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    if (!nlInput.trim()) return;
    setLoading(true);
    setGeneratedDescription(null);

    // Mock API call -- replace with real endpoint later
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const mockDescription = `Workflow generated from: "${nlInput.trim()}"

Steps:
1. Trigger: Listens for the described event
2. Research: Agent gathers context and relevant data
3. Action: Executes the primary integration calls
4. Approval: Human review for high-risk operations
5. Verify: Agent confirms successful completion`;

    setGeneratedDescription(mockDescription);

    // Generate mock nodes/edges for canvas preview
    setGeneratedGraph(
      [
        { id: "trigger-1", type: "trigger", position: { x: 0, y: 0 }, data: { label: "Event Trigger", triggerType: "webhook" as const, description: "Listens for the described event" } },
        { id: "agent-1", type: "agent", position: { x: 0, y: 0 }, data: { label: "Researcher", role: "researcher" as const, modelName: "claude-sonnet-4-20250514" } },
        { id: "action-1", type: "action", position: { x: 0, y: 0 }, data: { label: "Execute", provider: "Integration", toolName: "Run Action", riskLevel: "MEDIUM" as const } },
        { id: "approval-1", type: "approval", position: { x: 0, y: 0 }, data: { label: "Review", slaMinutes: 30 } },
        { id: "agent-2", type: "agent", position: { x: 0, y: 0 }, data: { label: "Verifier", role: "verifier" as const, modelName: "claude-sonnet-4-20250514" } },
      ],
      [
        { id: "e1-2", source: "trigger-1", target: "agent-1" },
        { id: "e2-3", source: "agent-1", target: "action-1" },
        { id: "e3-4", source: "action-1", target: "approval-1" },
        { id: "e4-5", source: "approval-1", target: "agent-2" },
      ]
    );

    setLoading(false);
  }, [nlInput, setGeneratedGraph]);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      {/* Input area */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-purple-500" />
          <h2 className="text-lg font-semibold text-foreground">Describe your workflow</h2>
        </div>
        <div className="flex gap-2">
          <Input
            value={nlInput}
            onChange={(e) => setNlInput(e.target.value)}
            placeholder="Describe what you want to automate..."
            className="flex-1"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !loading) handleSubmit();
            }}
          />
          <Button onClick={handleSubmit} disabled={loading || !nlInput.trim()}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Generate"
            )}
          </Button>
        </div>
      </div>

      {/* Example prompts */}
      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Examples
        </span>
        <div className="flex flex-col gap-1.5">
          {EXAMPLE_PROMPTS.map((example) => (
            <button
              key={example.category}
              type="button"
              onClick={() => setNlInput(example.text)}
              className="flex items-start gap-2 rounded-md px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <span className="mt-0.5 shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase">
                {example.category}
              </span>
              <span className="line-clamp-1">{example.text}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Generated description */}
      {generatedDescription && (
        <div className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-4">
          <h3 className="text-sm font-semibold text-foreground">Generated Workflow</h3>
          <pre className="whitespace-pre-wrap text-sm text-muted-foreground">
            {generatedDescription}
          </pre>
          {onPreviewCanvas && (
            <Button variant="outline" onClick={onPreviewCanvas} className="self-start">
              Preview on Canvas
              <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
