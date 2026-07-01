// Events the agent pushes to the caller's screen over the "onToolEvent" RPC method, in sync
// with the conversation. Field names mirror exactly what the agent emits (see the backend
// listing catalog + the agent's book_showing payload).

export interface Listing {
  code: string | null;
  address: string | null;
  price: number | null;
  beds: number | null;
  baths: number | null;
  sqft: number | null;
  description: string | null;
  image_url: string | null;
}

export interface ShortlistData {
  criteria: string;
  matches: Listing[];
}

export interface LeadData {
  name: string | null;
  phone: string | null;
  criteria: Record<string, unknown> | null;
}

export interface BookingData {
  propertyCode: string | null;
  address: string | null;
  startUtc: string | null;
  status: string | null;
  synced: boolean;
}

export type ToolEvent =
  | { type: "shortlist"; data: ShortlistData }
  | { type: "property"; data: Listing }
  | { type: "lead"; data: LeadData }
  | { type: "booking"; data: BookingData };

// Stable key for a listing (code preferred, address as fallback).
export function listingKey(l: Listing): string {
  return l.code ?? l.address ?? "";
}
