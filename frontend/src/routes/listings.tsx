import { useEffect, useState } from "react";
import { useOrganization } from "@clerk/clerk-react";
import { Building2, Link2, Loader2, Sparkles, Trash2, UploadCloud } from "lucide-react";
import {
  confirmOnboard,
  deleteListing,
  getLiveListings,
  listListings,
  onboard,
  onboardFromUrl,
  patchListing,
  type ListingDraft,
  type LiveListing,
  type RealtorProfile,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { curatedImage, houseImage } from "@/lib/house-images";

// A public synthetic realtor site so first-time users can watch onboarding work in one click,
// before they have their own site handy. Overridable per deploy.
const SAMPLE_URL =
  import.meta.env.VITE_SAMPLE_URL ?? "https://bluewater-homes-demo.vercel.app";

function priceLabel(price?: number | null): string {
  return price != null ? `$${price.toLocaleString()}` : "Price on request";
}

function specLine(l: LiveListing): string {
  const parts = [];
  if (l.beds != null) parts.push(`${l.beds} bed`);
  if (l.baths != null) parts.push(`${l.baths} bath`);
  if (l.sqft != null) parts.push(`${l.sqft.toLocaleString()} sqft`);
  return parts.join(" · ");
}

export default function Listings() {
  const { organization } = useOrganization();
  const realtor = organization?.name ?? "My agency";

  const [live, setLive] = useState<LiveListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [staged, setStaged] = useState<ListingDraft[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [status, setStatus] = useState("");
  const [crawling, setCrawling] = useState(false);
  const [importing, setImporting] = useState(false);
  const [profile, setProfile] = useState<RealtorProfile | null>(null);

  useEffect(() => {
    let active = true;
    getLiveListings()
      .then((l) => active && setLive(l))
      .catch(() => active && setError(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  function reload() {
    setLoading(true);
    setError(false);
    getLiveListings()
      .then(setLive)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }

  async function refreshLive() {
    setLive(await getLiveListings());
  }

  async function handleImport() {
    if (!file) {
      setStatus("Choose a CSV or PDF file first.");
      return;
    }
    if (!authorized) {
      setStatus("Please confirm these are your listings.");
      return;
    }
    setImporting(true);
    setProfile(null);
    setStatus("Reading your listings...");
    try {
      const res = await onboard(realtor, file);
      setStaged(res.listings);
      setStatus(
        `Imported ${res.listings.length} listing(s). Review, then go live.`,
      );
    } catch {
      setStatus("No listings could be read. Try a CSV or PDF file instead.");
    } finally {
      setImporting(false);
    }
  }

  async function runUrlOnboard(targetUrl: string, sample = false) {
    setCrawling(true);
    setStatus(
      sample
        ? "Reading our sample site, this can take a moment..."
        : "Reading your site, this can take up to a minute...",
    );
    try {
      const res = await onboardFromUrl(realtor, targetUrl);
      setStaged(res.listings);
      setProfile(res.profile ?? null);
      setStatus(
        res.listings.length
          ? `Found ${res.listings.length} listing(s)${sample ? " on the sample site" : " on your site"}. Review, then go live.`
          : "Couldn't find listings on that page. Try a specific listings page, or upload a file.",
      );
    } catch {
      setStatus(
        sample
          ? "Couldn't reach the sample site just now. Try again in a moment."
          : "Couldn't read that URL. Try another page, or upload a file.",
      );
    } finally {
      setCrawling(false);
    }
  }

  async function handleImportUrl() {
    if (!url.trim()) {
      setStatus("Paste your site URL first.");
      return;
    }
    if (!authorized) {
      setStatus("Please confirm these are your listings.");
      return;
    }
    // Accept a bare domain: the backend requires a scheme, so default to https.
    const raw = url.trim();
    const normalized = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
    await runUrlOnboard(normalized);
  }

  // Consent isn't required for the sample: it's our own site, offered for exactly this. Nothing
  // goes live either way; the pulled listings still land in the review buffer first.
  async function handleTrySample() {
    setUrl(SAMPLE_URL);
    await runUrlOnboard(SAMPLE_URL, true);
  }

  async function handleAddress(id: string, address: string) {
    try {
      await patchListing(realtor, id, { address });
      setStaged(await listListings(realtor));
    } catch {
      setStatus("Could not save that address, please try again.");
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteListing(realtor, id);
      setStaged(await listListings(realtor));
    } catch {
      setStatus("Could not remove that listing, please try again.");
    }
  }

  async function handleConfirm() {
    try {
      const res = await confirmOnboard(realtor);
      setStaged([]);
      setProfile(null);
      setStatus(`${res.inserted} listing(s) are now live to your assistant.`);
      await refreshLive();
    } catch {
      setStatus("Could not go live just now, please try again.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted-foreground">
        The homes your assistant knows. It only ever recommends these, grounded in your
        connected catalog.
      </p>
      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold tracking-tight">
            Your listings{" "}
            <span className="text-muted-foreground">
              {loading ? "" : `(${live.length})`}
            </span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Homes your assistant can recommend
          </p>
        </div>

        {loading ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Loading your homes...
          </p>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
              <p className="text-sm text-muted-foreground">
                Could not load your listings.
              </p>
              <Button variant="outline" size="sm" onClick={reload}>
                Retry
              </Button>
            </CardContent>
          </Card>
        ) : live.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
              <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <Building2 className="size-5" />
              </span>
              <p className="text-sm font-medium">No connected homes yet</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Connect your listings below and they will appear here, ready for
                the assistant to recommend on calls.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {live.map((l, i) => (
              <Card
                key={l.code ?? l.address ?? i}
                className="gap-0 overflow-hidden pt-0"
              >
                <img
                  src={houseImage(l)}
                  alt={l.address ?? "Home"}
                  loading="lazy"
                  onError={(e) => {
                    const el = e.currentTarget;
                    if (!el.dataset.fb) {
                      el.dataset.fb = "1";
                      el.src = curatedImage(l);
                    }
                  }}
                  className="h-40 w-full object-cover"
                />
                <CardContent className="space-y-2 pt-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {l.address ?? "Listing"}
                      </div>
                      <div className="text-sm font-semibold text-primary tabular-nums">
                        {priceLabel(l.price)}
                      </div>
                    </div>
                    {l.code && (
                      <Badge variant="muted" className="shrink-0 font-mono">
                        {l.code}
                      </Badge>
                    )}
                  </div>
                  {specLine(l) && (
                    <div className="text-xs text-muted-foreground">
                      {specLine(l)}
                    </div>
                  )}
                  {l.description && (
                    <p className="line-clamp-2 text-sm text-muted-foreground">
                      {l.description}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Connect listings</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {/* Primary path: paste a site/listings URL and we crawl it. */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">
              Paste your website or a listings page
            </label>
            <div className="flex gap-2">
              <Input
                type="url"
                placeholder="https://your-site.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={crawling || importing}
              />
              <Button
                className="shrink-0"
                onClick={() => void handleImportUrl()}
                disabled={crawling || importing}
              >
                {crawling ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Link2 />
                )}
                {crawling ? "Reading..." : "Fetch"}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              We read your own site and pull in every listing. You review it all
              before anything goes live.
            </p>
            <button
              type="button"
              onClick={() => void handleTrySample()}
              disabled={crawling || importing}
              className="self-start text-xs font-medium text-primary underline-offset-4 hover:underline disabled:opacity-60"
            >
              New here? Try it with our sample site &rarr;
            </button>
          </div>

          {/* Consent gates BOTH the URL fetch and the file upload, so it sits above both. */}
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={authorized}
              onChange={(e) => setAuthorized(e.target.checked)}
              className="size-4 rounded border-input accent-primary"
            />
            These are my listings and I am authorized to use them.
          </label>

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <div className="h-px flex-1 bg-border" />
            or upload a file
            <div className="h-px flex-1 bg-border" />
          </div>

          <input
            type="file"
            accept=".csv,.pdf,.html,text/html"
            disabled={importing || crawling}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full cursor-pointer rounded-md border border-input bg-background p-2 text-sm text-muted-foreground file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-secondary-foreground hover:file:bg-accent hover:file:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-60"
          />
          <div className="flex items-center gap-3">
            <Button
              onClick={() => void handleImport()}
              disabled={importing || crawling}
            >
              {importing ? (
                <Loader2 className="animate-spin" />
              ) : (
                <UploadCloud />
              )}
              {importing ? "Reading..." : "Import"}
            </Button>
            {status && <p className="text-sm text-muted-foreground">{status}</p>}
          </div>

          {profile &&
            (profile.name || profile.agency || profile.area || profile.tagline) && (
              <div className="rounded-lg border border-primary/30 bg-accent/40 p-3">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <Sparkles className="size-4 text-primary" /> From your site
                </div>
                <div className="mt-1 text-sm">
                  {[profile.name, profile.agency].filter(Boolean).join(" · ")}
                  {profile.area ? ` · ${profile.area}` : ""}
                </div>
                {profile.tagline && (
                  <p className="text-sm text-muted-foreground">"{profile.tagline}"</p>
                )}
                {profile.tone && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Tone: {profile.tone}
                  </p>
                )}
              </div>
            )}

          {staged.length > 0 && (
            <div className="flex flex-col gap-2 border-t border-border pt-4">
              <div className="text-sm font-medium">
                Review {staged.length} listing{staged.length === 1 ? "" : "s"}
              </div>
              {staged.map((l) => (
                <div
                  key={l.id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-border p-3"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <input
                      className="w-full rounded-sm bg-transparent text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                      defaultValue={l.address}
                      onBlur={(e) => void handleAddress(l.id, e.target.value)}
                    />
                    <div className="font-mono text-xs tabular-nums text-muted-foreground">
                      {priceLabel(l.price)} · {l.beds ?? "?"} bed ·{" "}
                      {l.baths ?? "?"} bath
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Remove listing"
                    className="text-muted-foreground hover:text-destructive"
                    onClick={() => void handleDelete(l.id)}
                  >
                    <Trash2 />
                  </Button>
                </div>
              ))}
              <Button className="mt-2 w-fit" onClick={() => void handleConfirm()}>
                Confirm and go live
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
