import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useSession, useSessionContext } from "@livekit/components-react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AgentSessionProvider } from "@/components/agents-ui/agent-session-provider";
import { AGENT_NAME, tokenSource, tokenSourceForTenant } from "@/lib/token-source";
import { Welcome } from "@/components/app/welcome";
import { SessionView } from "@/components/app/session-view";

function CallShell({ onSetPhone }: { onSetPhone?: (phone: string) => void }) {
  // The view switches on room-connection state. Ending the call disconnects the room,
  // which flips isConnected to false and returns to the welcome screen cleanly.
  const session = useSessionContext();
  if (!session.isConnected) {
    // Hand the entered number to the token source, then connect. The token request runs
    // inside start(), so the number is set before it is read.
    return (
      <Welcome
        onStart={(phone) => {
          onSetPhone?.(phone);
          void session.start();
        }}
      />
    );
  }
  return <SessionView onDisconnect={() => void session.end()} />;
}

export default function Call({ embed = false }: { embed?: boolean }) {
  // A buyer reaches a realtor's assistant at /call/:tenantSlug (tenantSlug = the realtor's
  // org id). That tenant is baked into the room name so the agent scopes memory to this
  // realtor. The bare /call route stays a no-tenant demo. In embed mode the widget renders
  // standalone (no public header), so it fills the whole iframe.
  const { tenantSlug } = useParams();
  // The tenant source carries a setter for the buyer's number (held inside the source's own
  // closure, so no React ref/state is shared into render). The no-tenant demo source can't
  // scope memory, so it has no phone step.
  const tenantSource = useMemo(
    () => (tenantSlug ? tokenSourceForTenant(tenantSlug) : null),
    [tenantSlug],
  );
  const session = useSession(tenantSource?.source ?? tokenSource, {
    agentName: AGENT_NAME,
  });
  return (
    <TooltipProvider>
      <AgentSessionProvider session={session}>
        <main className={embed ? "min-h-svh" : "min-h-[calc(100svh-3.5rem)]"}>
          <CallShell onSetPhone={tenantSource?.setBuyerPhone} />
        </main>
      </AgentSessionProvider>
    </TooltipProvider>
  );
}
