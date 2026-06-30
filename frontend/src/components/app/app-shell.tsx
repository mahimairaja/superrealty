import { NavLink, Outlet } from "react-router-dom";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/onboard", label: "Listings" },
  { to: "/call", label: "Assistant" },
  { to: "/pipeline", label: "Pipeline" },
];

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
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                    isActive && "bg-accent text-accent-foreground",
                  )
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
