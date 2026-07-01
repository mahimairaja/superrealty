import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RedirectToSignIn, SignedIn, SignedOut } from "@clerk/clerk-react";
import { AppShell } from "@/components/app/app-shell";
import { DashboardShell } from "@/components/app/dashboard-shell";
import Hub from "@/components/app/hub";
import Buyers from "@/routes/buyers";
import Call from "@/routes/call";
import Listings from "@/routes/listings";
import Overview from "@/routes/overview";
import Pipeline from "@/routes/pipeline";
import Settings from "@/routes/settings";

// The realtor console requires a signed-in user (an active organization = the tenant is
// gated inside DashboardShell). The landing and the buyer call widget stay public.
function Protected({ children }: { children: ReactNode }) {
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </>
  );
}

// Signed-out visitors see the marketing landing; a signed-in realtor goes to the dashboard.
function Landing() {
  return (
    <>
      <SignedIn>
        <Navigate to="/overview" replace />
      </SignedIn>
      <SignedOut>
        <Hub />
      </SignedOut>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public: slim chrome */}
        <Route element={<AppShell />}>
          <Route path="/" element={<Landing />} />
          <Route path="/call" element={<Call />} />
          {/* A realtor's public buyer line: the tenant slug scopes the agent's memory. */}
          <Route path="/call/:tenantSlug" element={<Call />} />
        </Route>

        {/* Console: left-sidebar dashboard */}
        <Route
          element={
            <Protected>
              <DashboardShell />
            </Protected>
          }
        >
          <Route path="/overview" element={<Overview />} />
          <Route path="/listings" element={<Listings />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/buyers" element={<Buyers />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        {/* Keep the removed v1 path alive, and never dead-end on an unknown URL. */}
        <Route path="/onboard" element={<Navigate to="/listings" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
