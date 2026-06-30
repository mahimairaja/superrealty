import { describe, expect, it } from "vitest";
import { API_BASE } from "./api";

describe("api", () => {
  it("derives the API base from the token endpoint", () => {
    expect(API_BASE.endsWith("/api/v1")).toBe(true);
    expect(API_BASE.endsWith("/token")).toBe(false);
  });
});
