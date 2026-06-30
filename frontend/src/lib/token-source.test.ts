import { afterEach, describe, expect, it, vi } from "vitest";
import { tokenSourceForTenant } from "./token-source";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("tokenSourceForTenant", () => {
  it("posts the tenant slug and agent dispatch, and maps the response", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({ server_url: "wss://lk", participant_token: "jwt-123" }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const source = tokenSourceForTenant("org_abc");
    const result = await source.fetch({ agentName: "realty" });

    expect(result.serverUrl).toBe("wss://lk");
    expect(result.participantToken).toBe("jwt-123");

    const [, init] = fetchMock.mock.calls[0];
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.tenant).toBe("org_abc");
    expect(body.room_config.agents[0].agent_name).toBe("realty");
  });

  it("throws when the token endpoint rejects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("nope", { status: 404 })),
    );
    const source = tokenSourceForTenant("org_missing");
    await expect(source.fetch({ agentName: "realty" })).rejects.toThrow(/404/);
  });
});
