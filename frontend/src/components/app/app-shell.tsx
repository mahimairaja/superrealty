import { NavLink, Outlet } from "react-router-dom";
import {
  OrganizationSwitcher,
  SignedIn,
  SignedOut,
  SignInButton,
  UserButton,
} from "@clerk/clerk-react";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function navClass({ isActive }: { isActive: boolean }) {
  return cn(
    "rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
    isActive && "bg-accent text-accent-foreground",
  );
}

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
          <nav className="hidden items-center gap-1 sm:flex">
            <NavLink to="/call" className={navClass}>
              Assistant
            </NavLink>
            <SignedIn>
              <NavLink to="/onboard" className={navClass}>
                Listings
              </NavLink>
              <NavLink to="/pipeline" className={navClass}>
                Pipeline
              </NavLink>
            </SignedIn>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <SignedIn>
              <OrganizationSwitcher
                hidePersonal
                afterSelectOrganizationUrl="/pipeline"
                afterCreateOrganizationUrl="/pipeline"
              />
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
