// Backend API client. The base is the LiveKit token endpoint minus the trailing /token,
// so the whole app points at one backend without extra config.
const TOKEN_ENDPOINT =
  import.meta.env.VITE_TOKEN_ENDPOINT ?? "http://localhost:8000/api/v1/token";

export const API_BASE = TOKEN_ENDPOINT.replace(/\/token$/, "");

// Console requests carry the Clerk session JWT; the backend resolves the tenant from it.
// The public buyer call widget (token-source) stays unauthenticated.
async function authHeaders(): Promise<Record<string, string>> {
  const clerk = (
    window as unknown as {
      Clerk?: { session?: { getToken: () => Promise<string | null> } };
    }
  ).Clerk;
  const token = clerk?.session ? await clerk.session.getToken() : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface ListingDraft {
  id: string;
  code?: string | null;
  address: string;
  price?: number | null;
  beds?: number | null;
  baths?: number | null;
  sqft?: number | null;
  description?: string | null;
  area?: string | null;
}

export interface OnboardResponse {
  realtor: string;
  listings: ListingDraft[];
}

export interface PipelineBooking {
  id?: number | null;
  address?: string | null;
  status: string;
  start_utc?: string | null;
  phone?: string | null;
}

export interface PipelineCall {
  id?: number | null;
  room_name: string;
  outcome?: string | null;
  buyer_phone?: string | null;
  ended_at?: string | null;
}

export interface PipelineResponse {
  bookings: PipelineBooking[];
  calls: PipelineCall[];
}

async function asJSON<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) throw new Error(`${what} failed: ${res.status}`);
  return (await res.json()) as T;
}

function withRealtor(path: string, realtor: string): string {
  const sep = path.includes("?") ? "&" : "?";
  return `${API_BASE}${path}${sep}realtor=${encodeURIComponent(realtor)}`;
}

export async function onboard(realtor: string, file: File): Promise<OnboardResponse> {
  const form = new FormData();
  form.set("realtor", realtor);
  form.set("authorized", "true");
  form.set("file", file);
  const res = await fetch(`${API_BASE}/onboard`, {
    method: "POST",
    body: form,
    headers: await authHeaders(),
  });
  return asJSON<OnboardResponse>(res, "onboard");
}

export async function listListings(realtor: string): Promise<ListingDraft[]> {
  const res = await fetch(withRealtor("/listings", realtor), {
    headers: await authHeaders(),
  });
  return asJSON<ListingDraft[]>(res, "listListings");
}

export async function patchListing(
  realtor: string,
  id: string,
  patch: Partial<ListingDraft>,
): Promise<ListingDraft> {
  const res = await fetch(withRealtor(`/listings/${id}`, realtor), {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(patch),
  });
  return asJSON<ListingDraft>(res, "patchListing");
}

export async function deleteListing(realtor: string, id: string): Promise<void> {
  const res = await fetch(withRealtor(`/listings/${id}`, realtor), {
    method: "DELETE",
    headers: await authHeaders(),
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`deleteListing failed: ${res.status}`);
  }
}

export async function confirmOnboard(
  realtor: string,
): Promise<{ realtor: string; inserted: number }> {
  const form = new FormData();
  form.set("realtor", realtor);
  const res = await fetch(`${API_BASE}/onboard/confirm`, {
    method: "POST",
    body: form,
    headers: await authHeaders(),
  });
  return asJSON<{ realtor: string; inserted: number }>(res, "confirmOnboard");
}

export async function getPipeline(): Promise<PipelineResponse> {
  const res = await fetch(`${API_BASE}/pipeline`, {
    headers: await authHeaders(),
  });
  return asJSON<PipelineResponse>(res, "getPipeline");
}
