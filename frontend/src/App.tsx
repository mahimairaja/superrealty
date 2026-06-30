import type { ReactNode } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { RedirectToSignIn, SignedIn, SignedOut } from "@clerk/clerk-react";
import { AppShell } from "@/components/app/app-shell";
import Hub from "@/components/app/hub";
import Call from "@/routes/call";
import Onboard from "@/routes/onboard";
import Pipeline from "@/routes/pipeline";

// The realtor console (listings, pipeline) requires a signed-in user with an active
// organization (the tenant). The landing and the buyer call widget stay public.
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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Hub />} />
          <Route path="/call" element={<Call />} />
          {/* A realtor's public buyer line: the tenant slug scopes the agent's memory. */}
          <Route path="/call/:tenantSlug" element={<Call />} />
          <Route
            path="/onboard"
            element={
              <Protected>
                <Onboard />
              </Protected>
            }
          />
          <Route
            path="/pipeline"
            element={
              <Protected>
                <Pipeline />
              </Protected>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
