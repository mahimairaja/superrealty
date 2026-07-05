import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

vi.mock("@clerk/clerk-react", () => ({
  SignUpButton: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

import { StartFreeButton } from "@/components/marketing/start-free-button";

test("StartFreeButton renders the default label", () => {
  render(<StartFreeButton />);
  expect(screen.getByRole("button", { name: "Start free" })).toBeInTheDocument();
});

test("StartFreeButton accepts a custom label", () => {
  render(<StartFreeButton label="Start free today" />);
  expect(
    screen.getByRole("button", { name: "Start free today" }),
  ).toBeInTheDocument();
});
