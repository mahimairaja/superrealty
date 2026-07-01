import {
  listingKey,
  type BookingData,
  type LeadData,
  type Listing,
  type ToolEvent,
} from "@/lib/tool-events";

// Accumulated state of one call, built by folding tool events. The agent is the source of
// truth; the UI only accumulates (homes are never evicted mid-call) and tracks which home is
// currently in focus.
export interface CallData {
  candidates: Listing[];
  activeKey: string | null;
  lead: LeadData | null;
  booking: BookingData | null;
}

export const EMPTY_CALL_DATA: CallData = {
  candidates: [],
  activeKey: null,
  lead: null,
  booking: null,
};

function upsert(list: Listing[], item: Listing): Listing[] {
  const key = listingKey(item);
  const idx = list.findIndex((l) => listingKey(l) === key);
  if (idx === -1) return [...list, item];
  const next = list.slice();
  next[idx] = item;
  return next;
}

export function reduceCallData(prev: CallData, event: ToolEvent): CallData {
  switch (event.type) {
    case "shortlist": {
      let candidates = prev.candidates;
      for (const match of event.data.matches) candidates = upsert(candidates, match);
      return { ...prev, candidates };
    }
    case "property":
      return {
        ...prev,
        candidates: upsert(prev.candidates, event.data),
        activeKey: listingKey(event.data) || null,
      };
    case "lead":
      return { ...prev, lead: event.data };
    case "booking":
      return { ...prev, booking: event.data };
    default:
      return prev;
  }
}
