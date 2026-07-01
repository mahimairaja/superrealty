import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  CreateOrganization,
  OrganizationSwitcher,
  useOrganization,
  UserButton,
} from "@clerk/clerk-react";
import {
  Building2,
  LayoutDashboard,
  Menu,
  Settings,
  Users,
  Waypoints,
  X,
} from "lucide-react";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/listings", label: "Listings", icon: Building2 },
  { to: "/pipeline", label: "Pipeline", icon: Waypoints },
  { to: "/buyers", label: "Buyers", icon: Users },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

function pageTitle(pathname: string): string {
  return NAV.find((n) => pathname.startsWith(n.to))?.label ?? "Dashboard";
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-1 bg-sidebar text-sidebar-foreground">
      <NavLink
        to="/overview"
        onClick={onNavigate}
        className="flex h-14 shrink-0 items-center gap-2 px-5"
      >
        <img src="/brand-mark.svg" alt="" className="h-6 w-6" />
        <span className="text-[15px] font-semibold tracking-tight">
          Realty<span className="text-sidebar-primary">Recall</span>
        </span>
      </NavLink>

      <nav className="flex flex-1 flex-col gap-0.5 px-3 py-2">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                isActive &&
                  "bg-sidebar-accent text-sidebar-accent-foreground",
              )
            }
          >
            <item.icon className="size-4.5 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="flex items-center justify-between gap-2 border-t border-sidebar-border px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <UserButton />
          <OrganizationSwitcher
            hidePersonal
            afterSelectOrganizationUrl="/overview"
            afterCreateOrganizationUrl="/overview"
          />
        </div>
        <ThemeToggle />
      </div>
    </div>
  );
}

export function DashboardShell() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const { organization, isLoaded } = useOrganization();
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Give the mobile drawer the modal contract: Escape closes it, background scroll is
  // locked, focus moves into the drawer on open and back to the trigger on close.
  useEffect(() => {
    if (!open) return;
    const trigger = menuButtonRef.current;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      trigger?.focus();
    };
  }, [open]);

  return (
    <div className="min-h-svh bg-background lg:grid lg:grid-cols-[16rem_1fr]">
      {/* Desktop sidebar */}
      <aside className="hidden border-r border-sidebar-border lg:block">
        <div className="sticky top-0 h-svh">
          <SidebarBody />
        </div>
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-foreground/40"
            onClick={() => setOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            className="absolute inset-y-0 left-0 w-64 border-r border-sidebar-border shadow-xl"
          >
            <SidebarBody onNavigate={() => setOpen(false)} />
            <Button
              ref={closeButtonRef}
              variant="ghost"
              size="icon"
              className="absolute right-2 top-2.5"
              onClick={() => setOpen(false)}
              aria-label="Close menu"
            >
              <X className="size-4" />
            </Button>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-sm sm:px-6">
          <Button
            ref={menuButtonRef}
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="size-5" />
          </Button>
          <h1 className="text-base font-semibold tracking-tight">
            {pageTitle(pathname)}
          </h1>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:py-8">
          {isLoaded && !organization ? (
            <div className="flex flex-col items-center gap-6 py-10 text-center">
              <div className="space-y-1">
                <h2 className="text-xl font-semibold tracking-tight">
                  Create your agency
                </h2>
                <p className="text-sm text-muted-foreground">
                  Your organization is your workspace. Create one to connect
                  listings and get your buyer call link.
                </p>
              </div>
              <CreateOrganization afterCreateOrganizationUrl="/overview" />
            </div>
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  );
}
