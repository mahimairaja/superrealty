import { ClerkProvider } from "@clerk/clerk-react";
import { dark } from "@clerk/themes";
import type { ReactNode } from "react";
import { useTheme } from "@/lib/use-theme";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
if (!PUBLISHABLE_KEY) {
  throw new Error("Missing VITE_CLERK_PUBLISHABLE_KEY");
}

// Clerk's own widgets (UserButton, OrganizationSwitcher, CreateOrganization) don't read our CSS
// tokens, so in dark mode they need Clerk's dark baseTheme or they render light and unreadable.
export function ThemedClerkProvider({ children }: { children: ReactNode }) {
  const { theme } = useTheme();
  return (
    <ClerkProvider
      publishableKey={PUBLISHABLE_KEY!}
      afterSignOutUrl="/"
      appearance={theme === "dark" ? { baseTheme: dark } : undefined}
    >
      {children}
    </ClerkProvider>
  );
}
