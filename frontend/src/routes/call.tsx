import { useSession, useSessionContext } from "@livekit/components-react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AgentSessionProvider } from "@/components/agents-ui/agent-session-provider";
import { AGENT_NAME, tokenSource } from "@/lib/token-source";
import { Welcome } from "@/components/app/welcome";
import { SessionView } from "@/components/app/session-view";

function CallShell() {
  // The view switches on room-connection state. Ending the call disconnects the room,
  // which flips isConnected to false and returns to the welcome screen cleanly.
  const session = useSessionContext();
  if (!session.isConnected) {
    return <Welcome onStart={() => void session.start()} />;
  }
  return <SessionView onDisconnect={() => void session.end()} />;
}

export default function Call() {
  const session = useSession(tokenSource, { agentName: AGENT_NAME });
  return (
    <TooltipProvider>
      <AgentSessionProvider session={session}>
        <main className="min-h-[calc(100svh-3.5rem)]">
          <CallShell />
        </main>
      </AgentSessionProvider>
    </TooltipProvider>
  );
}
