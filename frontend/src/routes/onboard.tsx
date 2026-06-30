import { useState } from "react";
import {
  confirmOnboard,
  deleteListing,
  listListings,
  onboard,
  patchListing,
  type ListingDraft,
} from "@/lib/api";

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
    <main className="min-h-screen p-8 max-w-2xl mx-auto flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Connect your listings</h1>
      <input
        type="file"
        accept=".csv,.pdf,.html,text/html"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={authorized}
          onChange={(e) => setAuthorized(e.target.checked)}
        />
        These are my listings and I am authorized to use them.
      </label>
      <button className="underline w-fit" onClick={() => void handleImport()}>
        Import
      </button>
      {status && <p className="text-sm text-muted-foreground">{status}</p>}

      <ul className="flex flex-col gap-3">
        {listings.map((l) => (
          <li key={l.id} className="border rounded p-3 flex flex-col gap-1">
            <input
              className="font-medium bg-transparent border-b"
              defaultValue={l.address}
              onBlur={(e) => void handleAddress(l.id, e.target.value)}
            />
            <div className="text-sm">
              {l.price != null ? `$${l.price.toLocaleString()}` : "price n/a"} ·{" "}
              {l.beds ?? "?"} bed · {l.baths ?? "?"} bath
            </div>
            <button
              className="text-sm underline text-red-600 w-fit"
              onClick={() => void handleDelete(l.id)}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      {listings.length > 0 && (
        <button className="underline w-fit" onClick={() => void handleConfirm()}>
          Confirm and go live
        </button>
      )}
    </main>
  );
}
