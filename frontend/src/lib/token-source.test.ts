import { afterEach, describe, expect, it, vi } from "vitest";
import { tokenSourceForTenant } from "./token-source";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function mockFetch(): { getBody: () => Record<string, unknown> } {
  let sentBody = "";
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      sentBody = (init?.body as string) ?? "";
      return new Response(
        JSON.stringify({ server_url: "wss://lk", participant_token: "jwt-123" }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }),
  );
  return { getBody: () => JSON.parse(sentBody) };
}

describe("tokenSourceForTenant", () => {
  it("posts the tenant slug and agent dispatch, and maps the response", async () => {
    const { getBody } = mockFetch();

    const { source } = tokenSourceForTenant("org_abc");
    const result = await source.fetch({ agentName: "realty" });

    expect(result.serverUrl).toBe("wss://lk");
    expect(result.participantToken).toBe("jwt-123");

    const body = getBody();
    expect(body.tenant).toBe("org_abc");
    expect((body.room_config as { agents: { agent_name: string }[] }).agents[0].agent_name).toBe(
      "realty",
    );
    // No number entered: no buyer attribute is sent.
    expect(body.participant_attributes).toBeUndefined();
  });

  it("sends an entered number as the buyer.phone attribute, digits only", async () => {
    const { getBody } = mockFetch();

    const src = tokenSourceForTenant("org_abc");
    src.setBuyerPhone("(519) 555-0142");
    await src.source.fetch({ agentName: "realty" });

    expect(getBody().participant_attributes).toEqual({ "buyer.phone": "5195550142" });
  });

  it("omits the buyer attribute when the number is too short to be real", async () => {
    const { getBody } = mockFetch();

    const src = tokenSourceForTenant("org_abc");
    src.setBuyerPhone("123");
    await src.source.fetch({ agentName: "realty" });

    expect(getBody().participant_attributes).toBeUndefined();
  });

  it("throws when the token endpoint rejects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("nope", { status: 404 })),
    );
    const { source } = tokenSourceForTenant("org_missing");
    await expect(source.fetch({ agentName: "realty" })).rejects.toThrow(/404/);
  });
});
