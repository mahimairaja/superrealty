import { useEffect, useState } from "react";
import { useOrganization } from "@clerk/clerk-react";
import { Check, Code2, Copy, MessageSquare } from "lucide-react";
import { getSettings, updateSettings } from "@/lib/api";
import { CallLinkCard } from "@/components/app/call-link-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function Settings() {
  const { organization } = useOrganization();

  const [smsTo, setSmsTo] = useState("");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [copied, setCopied] = useState(false);

  const snippet = organization
    ? `<script src="${window.location.origin}/embed.js" data-org="${organization.id}" async></script>`
    : "";

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked (insecure context); the snippet stays visible to copy by hand.
    }
  }

  useEffect(() => {
    let active = true;
    getSettings()
      .then((s) => active && setSmsTo(s.sms_to ?? ""))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  async function handleSave() {
    setSaving(true);
    setStatus("");
    try {
      const s = await updateSettings({ sms_to: smsTo.trim() || null });
      setSmsTo(s.sms_to ?? "");
      setStatus("Saved.");
    } catch {
      setStatus("Enter a valid phone number, e.g. +15195550142.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Agency</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Name</span>
            <span className="font-medium">{organization?.name ?? "-"}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Members</span>
            <span className="font-medium tabular-nums">
              {organization?.membersCount ?? 1}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Plan</span>
            <Badge variant="muted">Free</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageSquare className="size-4 text-primary" /> Lead notifications
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            When a call ends, your assistant texts you the buyer's details so you
            can follow up fast. Where should it text?
          </p>
          <div className="flex gap-2">
            <Input
              type="tel"
              placeholder="+1 519 555 0142"
              value={smsTo}
              onChange={(e) => setSmsTo(e.target.value)}
              disabled={saving}
            />
            <Button
              className="shrink-0"
              onClick={() => void handleSave()}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
          {status && <p className="text-sm text-muted-foreground">{status}</p>}
        </CardContent>
      </Card>

      {organization && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Code2 className="size-4 text-primary" /> Embed on your site
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              Paste this before &lt;/body&gt; on your website to add a floating
              "Talk to us" button that opens your assistant.
            </p>
            <div className="flex items-start gap-2">
              <code className="min-w-0 flex-1 overflow-x-auto rounded-md border border-border bg-card px-3 py-2 text-xs text-foreground">
                {snippet}
              </code>
              <Button
                size="sm"
                variant="outline"
                className="shrink-0"
                onClick={() => void copySnippet()}
                aria-label="Copy embed snippet"
              >
                {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <CallLinkCard />
    </div>
  );
}
