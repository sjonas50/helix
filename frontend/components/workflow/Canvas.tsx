"use client";

import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type OnSelectionChangeFunc,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { TriggerNode } from "./nodes/TriggerNode";
import { ActionNode } from "./nodes/ActionNode";
import { ConditionNode } from "./nodes/ConditionNode";
import { ApprovalNode } from "./nodes/ApprovalNode";
import { AgentNode } from "./nodes/AgentNode";
import { useWorkflowStore } from "@/lib/store/workflowStore";

const nodeTypes = {
  trigger: TriggerNode,
  action: ActionNode,
  condition: ConditionNode,
  approval: ApprovalNode,
  agent: AgentNode,
};

const NODE_WIDTH = 220;
const NODE_HEIGHT = 100;

/** Auto-layout nodes using dagre (top-to-bottom). */
function getLayoutedElements(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 80 });

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  const layoutedNodes = nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

interface CanvasProps {
  initialNodes?: Node[];
  initialEdges?: Edge[];
  className?: string;
}

export function Canvas({ initialNodes = [], initialEdges = [], className }: CanvasProps) {
  const setSelectedNodeId = useWorkflowStore((s) => s.setSelectedNodeId);
  const setUnsavedChanges = useWorkflowStore((s) => s.setUnsavedChanges);

  const layouted = useMemo(
    () => getLayoutedElements(initialNodes, initialEdges),
    [initialNodes, initialEdges]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layouted.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layouted.edges);

  const onSelectionChange: OnSelectionChangeFunc = useCallback(
    ({ nodes: selectedNodes }) => {
      const selected = selectedNodes.length === 1 ? selectedNodes[0].id : null;
      setSelectedNodeId(selected);
    },
    [setSelectedNodeId]
  );

  const handleNodesChange: typeof onNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes);
      setUnsavedChanges(true);
    },
    [onNodesChange, setUnsavedChanges]
  );

  return (
    <div className={className ?? "h-[600px] w-full rounded-lg border bg-zinc-50 dark:bg-zinc-950"}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onSelectionChange={onSelectionChange}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Controls />
        <MiniMap
          nodeStrokeWidth={3}
          className="!bg-white dark:!bg-zinc-900"
        />
      </ReactFlow>
    </div>
  );
}
