import { useState } from "react";
import { Trash2, UploadCloud } from "lucide-react";
import {
  confirmOnboard,
  deleteListing,
  listListings,
  onboard,
  patchListing,
  type ListingDraft,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// M0 runs for a single realtor (no sign-in), so the realtor identity is a fixed label.
const REALTOR = "Riley";

export default function Onboard() {
  const [file, setFile] = useState<File | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [listings, setListings] = useState<ListingDraft[]>([]);
  const [status, setStatus] = useState("");

  async function refresh() {
    setListings(await listListings(REALTOR));
  }

  async function handleImport() {
    if (!file || !authorized) {
      setStatus("Choose a file and confirm these are your listings.");
      return;
    }
    setStatus("Reading your listings...");
    try {
      const res = await onboard(REALTOR, file);
      setListings(res.listings);
      setStatus(
        `Imported ${res.listings.length} listing(s). Review and correct, then confirm.`,
      );
    } catch {
      setStatus("No listings could be read. Try a CSV or PDF file instead.");
    }
  }

  async function handleAddress(id: string, address: string) {
    await patchListing(REALTOR, id, { address });
    await refresh();
  }

  async function handleDelete(id: string) {
    await deleteListing(REALTOR, id);
    await refresh();
  }

  async function handleConfirm() {
    const res = await confirmOnboard(REALTOR);
    setListings([]);
    setStatus(`${res.inserted} listing(s) are now live to the assistant.`);
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10 sm:px-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Connect your listings
        </h1>
        <p className="text-sm text-muted-foreground">
          Import your homes once. The assistant only ever recommends listings
          you have connected.
        </p>
      </div>

      <Card>
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
            {status && (
              <p className="text-sm text-muted-foreground">{status}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {listings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Review {listings.length} listing
              {listings.length === 1 ? "" : "s"}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {listings.map((l) => (
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
                    {l.price != null
                      ? `$${l.price.toLocaleString()}`
                      : "price n/a"}{" "}
                    · {l.beds ?? "?"} bed · {l.baths ?? "?"} bath
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
          </CardContent>
        </Card>
      )}
    </main>
  );
}
