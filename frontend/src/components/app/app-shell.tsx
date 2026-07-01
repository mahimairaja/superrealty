import { Link, NavLink, Outlet } from "react-router-dom";
import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/clerk-react";
import { ArrowRight } from "lucide-react";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Button } from "@/components/ui/button";

// Slim public chrome for the marketing landing and the buyer call page. The realtor console
// has its own left-sidebar layout (DashboardShell); a signed-in realtor gets a shortcut in.
export function AppShell() {
  return (
    <div className="min-h-svh bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2">
            <img src="/brand-mark.svg" alt="" className="h-6 w-6" />
            <span className="text-[15px] font-semibold tracking-tight">
              Realty<span className="text-primary">Recall</span>
            </span>
          </NavLink>
          <div className="ml-auto flex items-center gap-2">
            <SignedIn>
              <Button asChild size="sm" variant="outline">
                <Link to="/overview">
                  Dashboard <ArrowRight className="size-3.5" />
                </Link>
              </Button>
              <UserButton />
            </SignedIn>
            <SignedOut>
              <SignInButton mode="modal">
                <Button size="sm">Sign in</Button>
              </SignInButton>
            </SignedOut>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
