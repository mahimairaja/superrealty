import type { ComponentProps } from "react";
import { SignUpButton } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";

// The single swap point for the primary conversion action. Today it opens Clerk's
// self-serve sign-up modal (the same modal pattern app-shell uses for Sign in). If
// onboarding ever needs a human in the loop, swap the SignUpButton wrapper for an
// anchor to a waitlist and every CTA on the page changes at once.
type StartFreeButtonProps = {
  label?: string;
  size?: ComponentProps<typeof Button>["size"];
  variant?: ComponentProps<typeof Button>["variant"];
  className?: string;
};

export function StartFreeButton({
  label = "Start free",
  size = "lg",
  variant = "default",
  className,
}: StartFreeButtonProps) {
  return (
    <SignUpButton mode="modal">
      <Button size={size} variant={variant} className={className}>
        {label}
      </Button>
    </SignUpButton>
  );
}
