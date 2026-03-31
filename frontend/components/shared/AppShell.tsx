"use client";

import { Sidebar } from "@/components/shared/Sidebar";
import { Header } from "@/components/shared/Header";

interface AppShellProps {
  children: React.ReactNode;
  wsConnected?: boolean;
  pendingApprovals?: number;
}

export function AppShell({
  children,
  wsConnected = false,
  pendingApprovals = 0,
}: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar pendingApprovals={pendingApprovals} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header wsConnected={wsConnected} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
