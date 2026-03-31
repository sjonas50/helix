"use client";

import { useEffect } from "react";
import useWebSocket from "react-use-websocket";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/useAuth";
import { useWSStore } from "@/lib/store/wsStore";
import type { WSEvent } from "@/types/ws";

export function useHelixWebSocket() {
  const token = useAuth((s) => s.accessToken);
  const qc = useQueryClient();
  const setConnected = useWSStore((s) => s.setConnected);

  const wsUrl = token
    ? `${process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/ws"}?token=${token}`
    : null;

  const { lastJsonMessage, readyState } = useWebSocket(wsUrl, {
    shouldReconnect: () => true,
    reconnectAttempts: 10,
    reconnectInterval: (attempt: number) =>
      Math.min(1000 * 2 ** attempt, 30000),
  });

  useEffect(() => {
    setConnected(readyState === 1); // WebSocket.OPEN
  }, [readyState, setConnected]);

  useEffect(() => {
    if (!lastJsonMessage) return;
    const event = lastJsonMessage as WSEvent;

    switch (event.type) {
      case "approval_request":
        qc.invalidateQueries({ queryKey: ["approvals"] });
        break;
      case "workflow_status":
        qc.invalidateQueries({ queryKey: ["workflows"] });
        break;
      case "agent_activity":
        qc.invalidateQueries({ queryKey: ["audit"] });
        break;
    }
  }, [lastJsonMessage, qc]);

  return { readyState };
}
