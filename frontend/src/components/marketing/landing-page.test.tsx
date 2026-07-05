import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test, vi } from "vitest";

vi.mock("@clerk/clerk-react", () => ({
  SignUpButton: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

import LandingPage from "@/components/marketing/landing-page";

function renderPage() {
  render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
}

test("hero headline renders", () => {
  renderPage();
  expect(screen.getByText(/Never forget a buyer\./i)).toBeInTheDocument();
});

test("all three pricing tiers render", () => {
  renderPage();
  expect(screen.getByText("Starter")).toBeInTheDocument();
  expect(screen.getByText("$297")).toBeInTheDocument();
  expect(screen.getByText("Pro")).toBeInTheDocument();
  expect(screen.getByText("$597")).toBeInTheDocument();
  expect(screen.getByText("Brokerage")).toBeInTheDocument();
  expect(screen.getAllByText("Custom").length).toBeGreaterThan(0);
});

test("comparison differentiator row renders", () => {
  renderPage();
  expect(
    screen.getByText(/Remembers buyers \+ proactive match/i),
  ).toBeInTheDocument();
});

test("primary and secondary CTAs render", () => {
  renderPage();
  // Multiple Start free buttons exist (hero, pricing x3, final); at least one.
  expect(screen.getAllByRole("button", { name: "Start free" }).length).toBeGreaterThan(0);
  // Secondary try-live links point at /call.
  const liveLinks = screen
    .getAllByRole("link")
    .filter((a) => a.getAttribute("href") === "/call");
  expect(liveLinks.length).toBeGreaterThan(0);
});
