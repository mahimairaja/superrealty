import type { Listing } from "@/lib/tool-events";

// Curated stock house photos, used when a listing has no real image_url yet. Assignment is
// deterministic by the listing code, so a given home always shows the same photo.
const CURATED = [
  "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800&q=80",
  "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800&q=80",
  "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800&q=80",
  "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&q=80",
  "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&q=80",
  "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80",
];

function hash(text: string): number {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0;
  return Math.abs(h);
}

// A stable curated fallback photo for a listing (also used as the <img> onError target when
// a real image_url fails to load: a scraped URL can be http/hotlink-blocked/404/ad-blocked).
export function curatedImage(listing: Listing): string {
  const seed = listing.code ?? listing.address ?? "home";
  return CURATED[hash(seed) % CURATED.length];
}

// Real photo if the listing has one, else a stable curated fallback.
export function houseImage(listing: Listing): string {
  return listing.image_url ?? curatedImage(listing);
}

export function formatPrice(price: number | null): string {
  if (price == null) return "Price on request";
  return `$${Math.round(price).toLocaleString()}`;
}
