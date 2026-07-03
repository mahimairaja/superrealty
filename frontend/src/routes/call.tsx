import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useSession, useSessionContext } from "@livekit/components-react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AgentSessionProvider } from "@/components/agents-ui/agent-session-provider";
import { AGENT_NAME, tokenSource, tokenSourceForTenant } from "@/lib/token-source";
import { Welcome } from "@/components/app/welcome";
import { SessionView } from "@/components/app/session-view";

// The connected call view; also covers the brief connecting gap after start(). Once a call has
// connected, any later disconnect (the hang-up button, an agent hang-up, or a dropped network)
// returns to the welcome screen so the caller can start again.
function Connected({ onEnd }: { onEnd: () => void }) {
  const session = useSessionContext();
  const wasConnected = useRef(false);
  useEffect(() => {
    if (session.isConnected) wasConnected.current = true;
    else if (wasConnected.current) onEnd();
  }, [session.isConnected, onEnd]);
  if (!session.isConnected) {
    return (
      <div className="grid min-h-[calc(100svh-3.5rem)] place-items-center p-6">
        <p className="text-sm text-muted-foreground">Connecting...</p>
      </div>
    );
  }
  return <SessionView onDisconnect={() => void session.end()} />;
}

// Mounted only AFTER the buyer's number is captured. useSession mints the token as soon as it
// mounts, so the source must already carry the number: that is why this is a separate component
// created with the phone baked in, rather than setting the phone later on a shared source.
function LiveCall({
  tenantSlug,
  phone,
  onEnd,
}: {
  tenantSlug: string | undefined;
  phone: string;
  onEnd: () => void;
}) {
  const source = useMemo(
    () => (tenantSlug ? tokenSourceForTenant(tenantSlug, phone) : tokenSource),
    [tenantSlug, phone],
  );
  const session = useSession(source, { agentName: AGENT_NAME });
  // Connect once, on mount. The token (with the phone attribute) is already prepared by then.
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void session.start();
  }, [session]);
  return (
    <AgentSessionProvider session={session}>
      <Connected onEnd={onEnd} />
    </AgentSessionProvider>
  );
}

export default function Call({ embed = false }: { embed?: boolean }) {
  // A buyer reaches a realtor's assistant at /call/:tenantSlug (tenantSlug = the realtor's
  // org id). That tenant is baked into the room name so the agent scopes memory to this
  // realtor. The bare /call route stays a no-tenant demo. In embed mode the widget renders
  // standalone (no public header), so it fills the whole iframe.
  const { tenantSlug } = useParams();
  // The welcome screen collects the number first; only then do we mount the session, so the
  // token carries buyer.phone and the agent can recognize a returning caller at connect.
  const [phone, setPhone] = useState<string | null>(null);
  return (
    <TooltipProvider>
      <main className={embed ? "min-h-svh" : "min-h-[calc(100svh-3.5rem)]"}>
        {phone === null ? (
          <Welcome onStart={setPhone} />
        ) : (
          <LiveCall
            tenantSlug={tenantSlug}
            phone={phone}
            onEnd={() => setPhone(null)}
          />
        )}
      </main>
    </TooltipProvider>
  );
}
