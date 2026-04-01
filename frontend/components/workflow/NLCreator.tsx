"use client";

import { useState } from "react";
import { Loader2, Sparkles, ArrowRight, AlertTriangle, CheckCircle2, Rocket, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useWorkflowStore } from "@/lib/store/workflowStore";
import { useGenerateWorkflow } from "@/lib/api/generate";
import { useDeployWorkflow, useRunWorkflow } from "@/lib/api/workflows";
import type { GeneratedWorkflow, WorkflowNode } from "@/lib/api/generate";

const EXAMPLE_PROMPTS = [
  { category: "Sales", text: "When a deal closes in Salesforce, create an onboarding project in Jira and notify the CS team in Slack" },
  { category: "Support", text: "When a critical Zendesk ticket is created, research the customer history in Salesforce, draft a response, and escalate if SLA is breached" },
  { category: "DevOps", text: "When a GitHub PR is merged to main, create a Jira ticket to track the deploy, and notify the team in Slack" },
  { category: "HR", text: "When a new employee is added, invite them to Slack, create their Jira account, and add them to the GitHub org" },
  { category: "Finance", text: "Every month-end, pull opportunity data from Salesforce, generate a revenue summary in Google Docs, and post it to the finance Slack channel" },
];

const RISK_COLORS: Record<string, string> = {
  LOW: "bg-green-100 text-green-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
  HIGH: "bg-orange-100 text-orange-800",
  CRITICAL: "bg-red-100 text-red-800",
};

function NodeSummary({ node }: { node: WorkflowNode }) {
  const typeIcons: Record<string, string> = {
    trigger: "⚡",
    action: "🔧",
    condition: "🔀",
    approval: "✋",
    agent: "🤖",
  };

  return (
    <div className="flex items-start gap-2 rounded-md border bg-background p-2">
      <span className="mt-0.5 text-base">{typeIcons[node.type] || "•"}</span>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{node.label}</span>
          {node.risk_level && (
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${RISK_COLORS[node.risk_level] || ""}`}>
              {node.risk_level}
            </span>
          )}
          {node.provider && (
            <span className="text-[10px] text-muted-foreground">{node.provider}</span>
          )}
        </div>
        {node.description && (
          <p className="mt-0.5 text-xs text-muted-foreground">{node.description}</p>
        )}
      </div>
    </div>
  );
}

interface NLCreatorProps {
  onPreviewCanvas?: () => void;
}

export function NLCreator({ onPreviewCanvas }: NLCreatorProps) {
  const nlInput = useWorkflowStore((s) => s.nlInput);
  const setNlInput = useWorkflowStore((s) => s.setNlInput);
  const setGeneratedGraph = useWorkflowStore((s) => s.setGeneratedGraph);

  const [result, setResult] = useState<GeneratedWorkflow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deployedId, setDeployedId] = useState<string | null>(null);

  const generateMutation = useGenerateWorkflow();
  const deployMutation = useDeployWorkflow();
  const runMutation = useRunWorkflow();

  const handleDeploy = () => {
    if (!result) return;
    deployMutation.mutate(
      { name: result.name, description: result.description, workflow_json: JSON.stringify(result) },
      { onSuccess: (data) => setDeployedId(data.id) }
    );
  };

  const handleRun = () => {
    if (!deployedId) return;
    runMutation.mutate(deployedId);
  };

  const handleSubmit = async () => {
    if (!nlInput.trim()) return;
    setResult(null);
    setError(null);
    setDeployedId(null);

    generateMutation.mutate(nlInput.trim(), {
      onSuccess: (data) => {
        setResult(data);
        setGeneratedGraph(
          data.nodes.map((n) => ({
            id: n.id,
            type: n.type,
            position: { x: 0, y: 0 },
            data: {
              label: n.label,
              description: n.description,
              provider: n.provider || undefined,
              toolName: n.tool_name || undefined,
              riskLevel: (n.risk_level || "LOW") as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
              triggerType: (n.trigger_type || "webhook") as "webhook" | "schedule" | "manual",
              role: (n.agent_role || "researcher") as "coordinator" | "researcher" | "implementer" | "verifier",
              modelName: "claude-sonnet-4-6",
              slaMinutes: n.sla_minutes || 30,
              conditionText: n.condition_text || "",
            },
          })),
          data.edges.map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            label: e.label || undefined,
          })),
        );
      },
      onError: (err) => {
        setError(err instanceof Error ? err.message : "Failed to generate workflow");
      },
    });
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
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
              if (e.key === "Enter" && !generateMutation.isPending) handleSubmit();
            }}
          />
          <Button onClick={handleSubmit} disabled={generateMutation.isPending || !nlInput.trim()}>
            {generateMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Generate"
            )}
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Examples</span>
        <div className="flex flex-col gap-1.5">
          {EXAMPLE_PROMPTS.map((example) => (
            <button
              key={example.category}
              type="button"
              onClick={() => setNlInput(example.text)}
              className="flex items-start gap-2 rounded-md px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <span className="mt-0.5 shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase">{example.category}</span>
              <span className="line-clamp-1">{example.text}</span>
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-4 rounded-lg border bg-muted/30 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">{result.name}</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">{result.description}</p>
            </div>
            <Badge className={RISK_COLORS[result.estimated_risk] || ""}>{result.estimated_risk} risk</Badge>
          </div>

          {result.integrations_used.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.integrations_used.map((i) => (
                <Badge key={i} variant="outline" className="text-xs">{i.replace("_", " ")}</Badge>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Steps ({result.nodes.length})</span>
            {result.nodes.map((node) => (
              <NodeSummary key={node.id} node={node} />
            ))}
          </div>

          <div className="flex items-center gap-2">
            {onPreviewCanvas && (
              <Button onClick={onPreviewCanvas} className="gap-1">
                <CheckCircle2 className="h-4 w-4" />
                Preview on Canvas
                <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            )}

            <Button variant="default" onClick={handleDeploy} disabled={deployMutation.isPending || !!deployedId}>
              {deployMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Rocket className="h-4 w-4" />}
              {deployedId ? "Deployed" : "Deploy Workflow"}
            </Button>

            {deployedId && (
              <Button onClick={handleRun} disabled={runMutation.isPending}>
                {runMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Run Now
              </Button>
            )}

            {runMutation.isSuccess && (
              <Badge className="bg-green-100 text-green-800">Executing...</Badge>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
