import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useSession, useSessionContext } from "@livekit/components-react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AgentSessionProvider } from "@/components/agents-ui/agent-session-provider";
import { AGENT_NAME, tokenSource, tokenSourceForTenant } from "@/lib/token-source";
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
  // A buyer reaches a realtor's assistant at /call/:tenantSlug (tenantSlug = the realtor's
  // org id). That tenant is baked into the room name so the agent scopes memory to this
  // realtor. The bare /call route stays a no-tenant demo.
  const { tenantSlug } = useParams();
  const source = useMemo(
    () => (tenantSlug ? tokenSourceForTenant(tenantSlug) : tokenSource),
    [tenantSlug],
  );
  const session = useSession(source, { agentName: AGENT_NAME });
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
