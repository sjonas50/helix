"use client";

import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { NLCreator } from "@/components/workflow/NLCreator";
import { Canvas } from "@/components/workflow/Canvas";
import { NodeConfigPanel } from "@/components/workflow/NodeConfigPanel";
import { useWorkflowStore } from "@/lib/store/workflowStore";

export default function NewWorkflowPage() {
  const [activeTab, setActiveTab] = useState<string>("describe");
  const generatedNodes = useWorkflowStore((s) => s.generatedNodes);
  const generatedEdges = useWorkflowStore((s) => s.generatedEdges);

  const handlePreviewCanvas = () => {
    setActiveTab("build");
  };

  return (
    <div className="flex flex-col gap-4 p-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">New Workflow</h1>
        <p className="text-sm text-muted-foreground">
          Describe what you want to automate or build visually on the canvas.
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
                // In a full implementation, update the node in store
                console.log("Save node", nodeId, data);
              }}
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
