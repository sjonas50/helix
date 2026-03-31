"use client";

interface ApprovalBadgeProps {
  count: number;
}

export function ApprovalBadge({ count }: ApprovalBadgeProps) {
  if (count <= 0) return null;

  return (
    <span className="inline-flex size-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white animate-pulse">
      {count > 99 ? "99+" : count}
    </span>
  );
}
