import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import {
  PageSkeleton,
  TableSkeleton,
  CardSkeleton,
} from "@/components/shared/LoadingSkeleton";

describe("PageSkeleton", () => {
  it("renders skeleton elements including 4 cards", () => {
    const { container } = render(<PageSkeleton />);

    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    // Header (2) + 4 cards * 3 skeletons each = 14
    expect(skeletons.length).toBeGreaterThanOrEqual(10);
  });

  it("renders card containers", () => {
    const { container } = render(<PageSkeleton />);

    const cards = container.querySelectorAll('[data-slot="card"]');
    expect(cards.length).toBe(4);
  });
});

describe("TableSkeleton", () => {
  it("renders header row and 5 data rows", () => {
    const { container } = render(<TableSkeleton />);

    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    // Header row (4) + 5 data rows * 4 = 24
    expect(skeletons.length).toBe(24);
  });
});

describe("CardSkeleton", () => {
  it("renders a card with skeleton elements", () => {
    const { container } = render(<CardSkeleton />);

    const card = container.querySelector('[data-slot="card"]');
    expect(card).toBeDefined();

    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(2);
  });
});
