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
 */
export function tokenSourceForTenant(tenant: string) {
  return TokenSource.custom(async (options): Promise<TokenSourceResponseObject> => {
    const body: Record<string, unknown> = { tenant };
    if (options.agentName) {
      body.room_config = { agents: [{ agent_name: options.agentName }] };
    }
    if (options.participantName) body.participant_name = options.participantName;
    if (options.participantIdentity) {
      body.participant_identity = options.participantIdentity;
    }
    const res = await fetch(TOKEN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
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
  });
}
