import { useEffect } from "react";
import { useMaybeRoomContext } from "@livekit/components-react";
import { RpcError, type RpcInvocationData } from "livekit-client";
import type { ToolEvent } from "@/lib/tool-events";

// Register the "onToolEvent" RPC method so the agent can push UI updates (house cards,
// booking, simulated SMS) to this screen during the call. The handler parses the JSON
// payload and hands it to onEvent; an unparseable payload is rejected so the agent logs it.
export function useToolEvents(onEvent: (event: ToolEvent) => void) {
  const room = useMaybeRoomContext();

  useEffect(() => {
    if (!room) return;
    const handler = async (data: RpcInvocationData): Promise<string> => {
      let event: ToolEvent;
      try {
        event = JSON.parse(data.payload) as ToolEvent;
      } catch {
        throw new RpcError(1, "invalid onToolEvent payload");
      }
      onEvent(event);
      return JSON.stringify({ ok: true });
    };
    room.registerRpcMethod("onToolEvent", handler);
    return () => {
      try {
        room.unregisterRpcMethod("onToolEvent");
      } catch {
        // already unregistered (e.g. React strict-mode double effect)
      }
    };
  }, [room, onEvent]);
}
