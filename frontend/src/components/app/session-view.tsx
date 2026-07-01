import { useReducer } from "react";
import {
  useAgent,
  useSessionContext,
  useSessionMessages,
} from "@livekit/components-react";
import { AgentAudioVisualizerBar } from "@/components/agents-ui/agent-audio-visualizer-bar";
import { AgentChatTranscript } from "@/components/agents-ui/agent-chat-transcript";
import { AgentControlBar } from "@/components/agents-ui/agent-control-bar";
import { BookingCard } from "@/components/app/booking-card";
import { HouseDetailCard } from "@/components/app/house-detail-card";
import { HouseShortlist } from "@/components/app/house-shortlist";
import { SmsPhone } from "@/components/app/sms-phone";
import { useToolEvents } from "@/hooks/use-tool-events";
import { EMPTY_CALL_DATA, reduceCallData } from "@/lib/call-data";
import { listingKey } from "@/lib/tool-events";

export function SessionView({ onDisconnect }: { onDisconnect: () => void }) {
  const { state, microphoneTrack } = useAgent();
  const { messages } = useSessionMessages();
  const { isConnected } = useSessionContext();

  // Fold the agent's tool events into call state; the panels appear as data arrives.
  const [callData, dispatch] = useReducer(reduceCallData, EMPTY_CALL_DATA);
  useToolEvents(dispatch);

  const active =
    callData.candidates.find((c) => listingKey(c) === callData.activeKey) ?? null;
  const hasHouses = callData.candidates.length > 0;
  const showContext = hasHouses || callData.booking != null;
  const showPhone = callData.lead != null || callData.booking != null;

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-4 p-4 lg:flex-row lg:items-start">
      {/* Voice column */}
      <div className="flex flex-1 flex-col gap-4 lg:sticky lg:top-4 lg:max-w-md">
        <div className="flex flex-col items-center gap-2 pt-6">
          <AgentAudioVisualizerBar
            state={state}
            audioTrack={microphoneTrack}
            barCount={5}
            size="lg"
          />
          <p className="text-sm text-muted-foreground">{state}</p>
        </div>

        <AgentChatTranscript
          messages={messages}
          agentState={state}
          className="max-h-[40vh] flex-1 overflow-y-auto rounded-lg border p-3 lg:max-h-[calc(100vh-16rem)]"
        />

        <AgentControlBar
          isConnected={isConnected}
          onDisconnect={onDisconnect}
          controls={{
            microphone: true,
            chat: true,
            leave: true,
            camera: false,
            screenShare: false,
          }}
        />
      </div>

      {/* House panel */}
      {showContext && (
        <div className="flex flex-1 flex-col gap-3 lg:max-w-sm">
          {hasHouses && (
            <HouseShortlist matches={callData.candidates} activeKey={callData.activeKey} />
          )}
          {active && <HouseDetailCard listing={active} />}
          {callData.booking && <BookingCard booking={callData.booking} />}
        </div>
      )}

      {/* Simulated SMS phone */}
      {showPhone && (
        <div className="shrink-0 lg:w-[280px]">
          <SmsPhone lead={callData.lead} booking={callData.booking} />
        </div>
      )}
    </div>
  );
}
