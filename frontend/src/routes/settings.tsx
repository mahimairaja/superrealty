import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useOrganization } from "@clerk/clerk-react";
import {
  ArrowRight,
  Check,
  Code2,
  Copy,
  Loader2,
  MessageSquare,
  RotateCcw,
} from "lucide-react";
import { getSettings, resetMemory, updateSettings } from "@/lib/api";
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
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetStatus, setResetStatus] = useState("");
  const [resetDone, setResetDone] = useState(false);

  async function handleReset() {
    setResetting(true);
    setResetStatus("");
    setResetDone(false);
    try {
      const { removed } = await resetMemory();
      setResetStatus(
        `Cleared ${removed} memory node${removed === 1 ? "" : "s"}. You're back to a blank slate.`,
      );
      setResetDone(true);
    } catch {
      setResetStatus("Could not reset just now, please try again.");
    } finally {
      setResetting(false);
      setConfirmReset(false);
    }
  }

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
      <p className="text-sm text-muted-foreground">
        Your agency details, where lead texts go, and how to embed the assistant on your site.
      </p>
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

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <RotateCcw className="size-4 text-destructive" /> Reset demo data
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            Permanently deletes every listing, buyer, and showing your assistant
            remembers, so you can re-onboard from scratch. This only affects your
            own agency and cannot be undone.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {confirmReset ? (
              <>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => void handleReset()}
                  disabled={resetting}
                >
                  {resetting ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <RotateCcw className="size-4" />
                  )}
                  {resetting ? "Resetting..." : "Yes, delete everything"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirmReset(false)}
                  disabled={resetting}
                >
                  Cancel
                </Button>
              </>
            ) : (
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setConfirmReset(true)}
              >
                <RotateCcw className="size-4" /> Reset demo data
              </Button>
            )}
          </div>
          {resetStatus && (
            <p className="text-sm text-muted-foreground">{resetStatus}</p>
          )}
          {resetDone && (
            <Button asChild size="sm" className="w-fit">
              <Link to="/listings">
                Start onboarding <ArrowRight className="size-4" />
              </Link>
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
