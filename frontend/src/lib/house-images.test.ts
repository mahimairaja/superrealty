import { describe, expect, it } from "vitest";
import { formatPrice, houseImage } from "./house-images";
import type { Listing } from "./tool-events";

const base: Listing = {
  code: "RR-1",
  address: "1 Street",
  price: null,
  beds: null,
  baths: null,
  sqft: null,
  description: null,
  image_url: null,
};

describe("houseImage", () => {
  it("uses the real image_url when the listing has one", () => {
    expect(houseImage({ ...base, image_url: "https://x/y.jpg" })).toBe("https://x/y.jpg");
  });

  it("falls back to a stable curated photo keyed by code", () => {
    const first = houseImage(base);
    expect(first).toContain("unsplash");
    expect(houseImage(base)).toBe(first); // deterministic
  });
});

describe("formatPrice", () => {
  it("formats a price and handles null", () => {
    expect(formatPrice(459000)).toBe("$459,000");
    expect(formatPrice(null)).toBe("Price on request");
  });
});
