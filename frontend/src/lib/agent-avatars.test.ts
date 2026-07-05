import { describe, expect, it } from "vitest";
import { AGENT_AVATARS, pickByAgentId } from "./agent-avatars";

describe("agent avatars", () => {
  it("ships 8 reusable avatars", () => {
    expect(AGENT_AVATARS).toHaveLength(8);
  });

  it("is deterministic for the same id", () => {
    expect(pickByAgentId("nurture")).toBe(pickByAgentId("nurture"));
  });

  it("always returns one of the set", () => {
    expect(AGENT_AVATARS).toContain(pickByAgentId("proactive-match"));
  });

  it("spreads the roster across more than one avatar", () => {
    const roster = [
      "intake", "qualification", "nurture", "proactive-match",
      "crm", "scheduling", "retention", "reactivation",
      "transaction", "closing", "seller", "feedback",
    ];
    const picked = new Set(roster.map(pickByAgentId));
    expect(picked.size).toBeGreaterThan(1);
  });

  it("falls back to the first avatar for an empty id", () => {
    expect(pickByAgentId("")).toBe(AGENT_AVATARS[0]);
  });
});
