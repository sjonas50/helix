import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

// Suppress console.error noise from React and our boundary during tests
vi.spyOn(console, "error").mockImplementation(() => {});

function ThrowingChild() {
  throw new Error("Test explosion");
  return null; // eslint-disable-line no-unreachable
}

describe("ErrorBoundary", () => {
  it("catches errors and shows fallback UI", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeDefined();
  });

  it('shows "Something went wrong" heading', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeDefined();
    expect(
      screen.getByText(/try refreshing the page/i),
    ).toBeDefined();
  });

  it('shows "Go back to Dashboard" link', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );

    const link = screen.getByText("Go back to Dashboard");
    expect(link).toBeDefined();
    expect(link.closest("a")).toBeDefined();
    expect(link.closest("a")?.getAttribute("href")).toBe("/");
  });

  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <p>All good</p>
      </ErrorBoundary>,
    );

    expect(screen.getByText("All good")).toBeDefined();
  });
});
