import { describe, expect, it } from "vitest";
import { EMPTY_CALL_DATA, reduceCallData } from "./call-data";
import type { Listing } from "./tool-events";

const home = (code: string, extra?: Partial<Listing>): Listing => ({
  code,
  address: `${code} Street`,
  price: 400000,
  beds: 3,
  baths: 2,
  sqft: 1200,
  description: null,
  image_url: null,
  ...extra,
});

describe("reduceCallData", () => {
  it("accumulates shortlist matches and upserts duplicates in place", () => {
    let s = reduceCallData(EMPTY_CALL_DATA, {
      type: "shortlist",
      data: { criteria: "x", matches: [home("A"), home("B")] },
    });
    expect(s.candidates.map((c) => c.code)).toEqual(["A", "B"]);

    s = reduceCallData(s, {
      type: "shortlist",
      data: { criteria: "y", matches: [home("B", { price: 999 }), home("C")] },
    });
    expect(s.candidates.map((c) => c.code)).toEqual(["A", "B", "C"]);
    expect(s.candidates.find((c) => c.code === "B")?.price).toBe(999);
  });

  it("focuses a property, sets activeKey, and adds it to candidates", () => {
    const s = reduceCallData(EMPTY_CALL_DATA, { type: "property", data: home("A") });
    expect(s.activeKey).toBe("A");
    expect(s.candidates).toHaveLength(1);
  });

  it("stores lead and booking without dropping the other", () => {
    let s = reduceCallData(EMPTY_CALL_DATA, {
      type: "lead",
      data: { name: "Dana", phone: "519", criteria: null },
    });
    s = reduceCallData(s, {
      type: "booking",
      data: {
        propertyCode: "A",
        address: "1 St",
        startUtc: "2026-07-05T18:00:00Z",
        status: "accepted",
        synced: true,
      },
    });
    expect(s.lead?.name).toBe("Dana");
    expect(s.booking?.status).toBe("accepted");
  });
});
