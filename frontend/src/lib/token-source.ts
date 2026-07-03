import { TokenSource, type TokenSourceResponseObject } from "livekit-client";

const TOKEN_ENDPOINT =
  import.meta.env.VITE_TOKEN_ENDPOINT ?? "http://localhost:8000/api/v1/token";

// Demo/default source: no tenant, so the backend names the room generically. The agent
// then has no realtor to scope memory to, so its listing recall is unavailable. Use
// tokenSourceForTenant for a real buyer call against a specific realtor.
export const tokenSource = TokenSource.endpoint(TOKEN_ENDPOINT);

// Must match the agent worker's agent_name (AGENT_NAME in the agent package).
export const AGENT_NAME = import.meta.env.VITE_AGENT_NAME ?? "realty";

/**
 * A token source for a buyer calling a specific realtor. It posts the realtor's tenant slug
 * (their Clerk org id) so the backend names the room t_{tenant}_{random}; the agent recovers
 * the tenant from that name and scopes every memory read/write to this realtor.
 *
 * Built on TokenSource.custom so we can include the tenant in the request body (the standard
 * endpoint source does not allow extra fields). Agent dispatch is packaged into room_config,
 * exactly as the endpoint source does it.
 *
 * `buyerPhone` is baked in at creation (the caller enters it before this source is made, since
 * useSession mints the token as soon as it mounts). When present it is sent as the `buyer.phone`
 * participant attribute so the agent recognizes a returning caller from the first word, like
 * SIP caller ID.
 */
export function tokenSourceForTenant(tenant: string, buyerPhone = "") {
  return TokenSource.custom(
    async (options): Promise<TokenSourceResponseObject> => {
      // Forward every option the backend RoomTokenRequest supports. roomName is intentionally
      // omitted: the tenant flow names the room server-side (t_{tenant}_{random}), so a client
      // room_name is ignored. agentMetadata is the agent dispatch's `metadata` proto field.
      const body: Record<string, unknown> = { tenant };
      const phone = buyerPhone.replace(/\D/g, "");
      if (phone.length >= 7) {
        body.participant_attributes = { "buyer.phone": phone };
      }
      if (options.agentName || options.agentMetadata) {
        const agent: Record<string, unknown> = {};
        if (options.agentName) agent.agent_name = options.agentName;
        if (options.agentMetadata) agent.metadata = options.agentMetadata;
        body.room_config = { agents: [agent] };
      }
      if (options.participantName) body.participant_name = options.participantName;
      if (options.participantIdentity) {
        body.participant_identity = options.participantIdentity;
      }
      if (options.participantMetadata) {
        body.participant_metadata = options.participantMetadata;
      }
      // Guard against a hung backend: without a timeout, LiveKit session start() could stall
      // indefinitely waiting on this token.
      let res: Response;
      try {
        res = await fetch(TOKEN_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(10000),
        });
      } catch (err) {
        if (err instanceof DOMException && err.name === "TimeoutError") {
          throw new Error("token request timed out after 10s", { cause: err });
        }
        throw err;
      }
      if (!res.ok) {
        throw new Error(`token request failed: ${res.status}`);
      }
      const data = (await res.json()) as {
        server_url: string;
        participant_token: string;
      };
      return {
        serverUrl: data.server_url,
        participantToken: data.participant_token,
      };
    },
  );
}
