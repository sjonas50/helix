import { create } from "zustand";
import type { Node, Edge } from "@xyflow/react";

interface WorkflowStore {
  /** Currently selected node on the canvas */
  selectedNodeId: string | null;
  setSelectedNodeId: (id: string | null) => void;

  /** Whether there are unsaved changes on the canvas */
  unsavedChanges: boolean;
  setUnsavedChanges: (dirty: boolean) => void;

  /** Natural language input from the NLCreator */
  nlInput: string;
  setNlInput: (input: string) => void;

  /** Nodes and edges generated from NL or loaded from API */
  generatedNodes: Node[];
  generatedEdges: Edge[];
  setGeneratedGraph: (nodes: Node[], edges: Edge[]) => void;
}

export const useWorkflowStore = create<WorkflowStore>((set) => ({
  selectedNodeId: null,
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),

  unsavedChanges: false,
  setUnsavedChanges: (dirty) => set({ unsavedChanges: dirty }),

  nlInput: "",
  setNlInput: (input) => set({ nlInput: input }),

  generatedNodes: [],
  generatedEdges: [],
  setGeneratedGraph: (nodes, edges) =>
    set({ generatedNodes: nodes, generatedEdges: edges }),
}));
