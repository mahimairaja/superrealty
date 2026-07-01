import { useEffect, useState } from "react";
import { useOrganization } from "@clerk/clerk-react";
import { Building2, Trash2, UploadCloud } from "lucide-react";
import {
  confirmOnboard,
  deleteListing,
  getLiveListings,
  listListings,
  onboard,
  patchListing,
  type ListingDraft,
  type LiveListing,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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
  const [authorized, setAuthorized] = useState(false);
  const [status, setStatus] = useState("");

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
    if (!file || !authorized) {
      setStatus("Choose a file and confirm these are your listings.");
      return;
    }
    setStatus("Reading your listings...");
    try {
      const res = await onboard(realtor, file);
      setStaged(res.listings);
      setStatus(
        `Imported ${res.listings.length} listing(s). Review, then go live.`,
      );
    } catch {
      setStatus("No listings could be read. Try a CSV or PDF file instead.");
    }
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
      setStatus(`${res.inserted} listing(s) are now live to your assistant.`);
      await refreshLive();
    } catch {
      setStatus("Could not go live just now, please try again.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
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
              <Card key={l.code ?? l.address ?? i} className="gap-3">
                <CardContent className="space-y-2">
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
          <input
            type="file"
            accept=".csv,.pdf,.html,text/html"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full cursor-pointer rounded-md border border-input bg-background p-2 text-sm text-muted-foreground file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-secondary-foreground hover:file:bg-accent hover:file:text-accent-foreground"
          />
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={authorized}
              onChange={(e) => setAuthorized(e.target.checked)}
              className="size-4 rounded border-input accent-primary"
            />
            These are my listings and I am authorized to use them.
          </label>
          <div className="flex items-center gap-3">
            <Button onClick={() => void handleImport()}>
              <UploadCloud /> Import
            </Button>
            {status && <p className="text-sm text-muted-foreground">{status}</p>}
          </div>

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
