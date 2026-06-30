import { useState } from "react";
import { useOrganization } from "@clerk/clerk-react";
import { Check, Copy, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/**
 * The realtor's shareable buyer line. The path carries their org id (the tenant slug), so a
 * buyer who opens it reaches an assistant scoped to this realtor's listings and memory.
 * Renders nothing until an organization is active (the tenant is not yet known otherwise).
 */
export function CallLinkCard() {
  const { organization } = useOrganization();
  const [copied, setCopied] = useState(false);

  if (!organization) return null;

  const link = `${window.location.origin}/call/${organization.id}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked (insecure context); the link stays visible to copy by hand.
    }
  }

  return (
    <Card className="border-primary/30 bg-accent/40">
      <CardContent className="flex flex-col gap-3">
        <span className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <Link2 className="size-4 text-primary" />
          Your buyer call link
        </span>
        <p className="text-sm text-muted-foreground">
          Share this link or put it on your listings. Buyers who open it reach
          your assistant, scoped to your homes.
        </p>
        <div className="flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-md border border-border bg-card px-3 py-2 text-xs text-foreground">
            {link}
          </code>
          <Button size="sm" variant="outline" onClick={copy} aria-label="Copy call link">
            {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
