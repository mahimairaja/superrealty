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

export interface RealtorProfile {
  name?: string | null;
  agency?: string | null;
  area?: string | null;
  tagline?: string | null;
  tone?: string | null;
}

export interface OnboardResponse {
  realtor: string;
  listings: ListingDraft[];
  profile?: RealtorProfile | null;
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

// Seed onboarding from a URL: the backend crawls the realtor's own site, extracts every
// listing, and infers a profile. Can take a while, so callers should show a loading state.
export async function onboardFromUrl(
  realtor: string,
  url: string,
): Promise<OnboardResponse> {
  const form = new FormData();
  form.set("realtor", realtor);
  form.set("authorized", "true");
  form.set("url", url);
  const res = await fetch(`${API_BASE}/onboard`, {
    method: "POST",
    body: form,
    headers: await authHeaders(),
  });
  return asJSON<OnboardResponse>(res, "onboardFromUrl");
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

export interface LiveListing {
  code?: string | null;
  address?: string | null;
  price?: number | null;
  beds?: number | null;
  baths?: number | null;
  sqft?: number | null;
  description?: string | null;
  image_url?: string | null;
}

// The realtor's connected homes read back from Cognee (what the assistant recommends).
export async function getLiveListings(): Promise<LiveListing[]> {
  const res = await fetch(`${API_BASE}/listings/live`, {
    headers: await authHeaders(),
  });
  return asJSON<LiveListing[]>(res, "getLiveListings");
}

export interface ListingCreate {
  address: string;
  price?: number | null;
  beds?: number | null;
  baths?: number | null;
  area?: string | null;
  description?: string | null;
}

// Add one home straight to the live catalog. It becomes the newest listing, so the "Buyers
// waiting" match card reflects it right away.
export async function addListing(payload: ListingCreate): Promise<LiveListing> {
  const res = await fetch(`${API_BASE}/listings`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(payload),
  });
  return asJSON<LiveListing>(res, "addListing");
}

export interface AccountSettings {
  sms_to?: string | null;
}

// The realtor's account settings (where post-call lead texts go).
export async function getSettings(): Promise<AccountSettings> {
  const res = await fetch(`${API_BASE}/settings`, { headers: await authHeaders() });
  return asJSON<AccountSettings>(res, "getSettings");
}

export async function updateSettings(
  patch: AccountSettings,
): Promise<AccountSettings> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(patch),
  });
  return asJSON<AccountSettings>(res, "updateSettings");
}

// The realtor's synthesized assistant persona (how the agent introduces itself on calls).
// All-null until they connect listings by URL and confirm.
export async function getAssistantPersona(): Promise<RealtorProfile> {
  const res = await fetch(`${API_BASE}/realtor/me`, {
    headers: await authHeaders(),
  });
  return asJSON<RealtorProfile>(res, "getAssistantPersona");
}

export interface BuyerSummary {
  phone?: string | null;
  name?: string | null;
  email?: string | null;
  criteria?: Record<string, unknown> | null;
}

export async function getBuyers(): Promise<BuyerSummary[]> {
  const res = await fetch(`${API_BASE}/buyers`, {
    headers: await authHeaders(),
  });
  return asJSON<BuyerSummary[]>(res, "getBuyers");
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  props: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  rel: string;
}

export interface MemoryGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// The realtor's Cognee memory subgraph (nodes + edges), scoped to their tenant.
export async function getGraph(): Promise<MemoryGraphData> {
  const res = await fetch(`${API_BASE}/graph`, { headers: await authHeaders() });
  return asJSON<MemoryGraphData>(res, "getGraph");
}

// Wipe the realtor's own memory (listings, buyers, showings) so they can re-onboard fresh.
// Tenant-scoped on the backend: it only removes this realtor's NodeSet. Returns nodes removed.
export async function resetMemory(): Promise<{ removed: number }> {
  const res = await fetch(`${API_BASE}/graph`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
  return asJSON<{ removed: number }>(res, "resetMemory");
}

export interface MatchReport {
  narrative: string;
  buyers: { name: string | null; phone: string | null }[];
  count: number;
}

// Which remembered buyers want a specific connected listing (graph match).
export async function getListingMatches(code: string): Promise<MatchReport> {
  const res = await fetch(`${API_BASE}/listings/${encodeURIComponent(code)}/matches`, {
    headers: await authHeaders(),
  });
  return asJSON<MatchReport>(res, "getListingMatches");
}

export interface Insight {
  title: string;
  body: string;
}

// Graph-wide market insights (Cognee SUMMARIES) for the dashboard.
export async function getInsights(): Promise<Insight[]> {
  const res = await fetch(`${API_BASE}/insights`, { headers: await authHeaders() });
  return asJSON<Insight[]>(res, "getInsights");
}
