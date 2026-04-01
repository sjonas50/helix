import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { AutonomyDial } from "@/components/shared/AutonomyDial";
import { NLCreator } from "@/components/workflow/NLCreator";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/workflows",
  useParams: () => ({ id: "test-id" }),
}));

// Mock @xyflow/react for Canvas test
vi.mock("@xyflow/react", () => ({
  ReactFlow: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="react-flow">{children}</div>
  ),
  Background: () => <div data-testid="rf-background" />,
  Controls: () => <div data-testid="rf-controls" />,
  MiniMap: () => <div data-testid="rf-minimap" />,
  Handle: () => <div />,
  Position: { Top: "top", Bottom: "bottom", Left: "left", Right: "right" },
  BackgroundVariant: { Dots: "dots" },
  useNodesState: (init: unknown[]) => [init, vi.fn(), vi.fn()],
  useEdgesState: (init: unknown[]) => [init, vi.fn(), vi.fn()],
}));

describe("AutonomyDial", () => {
  it("renders all 4 positions", () => {
    const onChange = vi.fn();
    render(<AutonomyDial value={1} onChange={onChange} />);

    expect(screen.getByRole("radio", { name: /Observe & Suggest/i })).toBeDefined();
    expect(screen.getByRole("radio", { name: /Plan & Propose/i })).toBeDefined();
    expect(screen.getByRole("radio", { name: /Act with Confirmation/i })).toBeDefined();
    expect(screen.getByRole("radio", { name: /Act Autonomously/i })).toBeDefined();
  });

  it("shows the current label text", () => {
    const onChange = vi.fn();
    render(<AutonomyDial value={3} onChange={onChange} />);

    expect(screen.getByText("Act with Confirmation")).toBeDefined();
  });

  it("calls onChange when a position is clicked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<AutonomyDial value={1} onChange={onChange} />);

    await user.click(screen.getByRole("radio", { name: /Act Autonomously/i }));
    expect(onChange).toHaveBeenCalledWith(4);
  });
});

// NLCreator needs QueryClientProvider since it uses useMutation
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
function withQueryClient(ui: React.ReactElement) {
  return <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>;
}

describe("NLCreator", () => {
  it("renders input and submit button", () => {
    render(withQueryClient(<NLCreator />));

    expect(screen.getByPlaceholderText("Describe what you want to automate...")).toBeDefined();
    expect(screen.getByRole("button", { name: /^Generate$/i })).toBeDefined();
  });

  it("renders example prompts", () => {
    render(withQueryClient(<NLCreator />));

    expect(screen.getByText("Sales")).toBeDefined();
    expect(screen.getByText("Support")).toBeDefined();
    expect(screen.getByText("DevOps")).toBeDefined();
  });

  it("disables submit when input is empty", () => {
    render(withQueryClient(<NLCreator />));

    const buttons = screen.getAllByRole("button");
    const generateBtn = buttons.find(b => b.textContent?.trim() === "Generate");
    expect(generateBtn).toBeDefined();
    expect(generateBtn).toBeDisabled();
  });
});

describe("Canvas", () => {
  it("renders without crashing", async () => {
    // Dynamic import after mock is set up
    const { Canvas } = await import("@/components/workflow/Canvas");
    render(<Canvas initialNodes={[]} initialEdges={[]} />);

    expect(screen.getByTestId("react-flow")).toBeDefined();
  });
});
