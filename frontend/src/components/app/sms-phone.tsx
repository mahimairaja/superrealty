import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { formatWhen } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import type { BookingData, LeadData } from "@/lib/tool-events";
import { cn } from "@/lib/utils";

type Side = "realtor" | "buyer";
interface Bubble {
  id: string;
  text: string;
}

function criteriaSummary(criteria: Record<string, unknown> | null): string {
  if (!criteria) return "a home";
  const parts: string[] = [];
  if (criteria.minBeds) parts.push(`${criteria.minBeds}+ bed`);
  if (criteria.area) parts.push(String(criteria.area));
  if (criteria.maxPrice) parts.push(`under $${Number(criteria.maxPrice).toLocaleString()}`);
  return parts.length ? parts.join(", ") : "a home";
}

function realtorMessages(lead: LeadData | null, booking: BookingData | null): Bubble[] {
  const out: Bubble[] = [];
  if (lead) {
    out.push({
      id: "lead",
      text: `New lead: ${lead.name ?? "a caller"}${lead.phone ? ` (${lead.phone})` : ""}. Looking for ${criteriaSummary(lead.criteria)}.`,
    });
  }
  if (booking) {
    out.push({
      id: "booking",
      text: `Showing booked${booking.address ? ` at ${booking.address}` : ""} for ${formatWhen(booking.startUtc)}.`,
    });
  }
  return out;
}

function buyerMessages(lead: LeadData | null, booking: BookingData | null): Bubble[] {
  const out: Bubble[] = [];
  if (booking) {
    out.push({
      id: "booking",
      text: `Hi${lead?.name ? ` ${lead.name}` : ""}, you're confirmed for a showing${booking.address ? ` at ${booking.address}` : ""} on ${formatWhen(booking.startUtc)}. Reply STOP to cancel.`,
    });
  }
  return out;
}

export function SmsPhone({
  lead,
  booking,
}: {
  lead: LeadData | null;
  booking: BookingData | null;
}) {
  const [side, setSide] = useState<Side>("realtor");
  const messages =
    side === "realtor" ? realtorMessages(lead, booking) : buyerMessages(lead, booking);
  const contact = side === "realtor" ? "Your realtor line" : "RealtyRecall";

  return (
    <div className="mx-auto w-full max-w-[260px]">
      <div className="mb-2 flex items-center justify-between">
        <div className="inline-flex rounded-lg bg-muted p-0.5 text-xs">
          {(["realtor", "buyer"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSide(s)}
              className={cn(
                "rounded-md px-2.5 py-1 font-medium capitalize transition-colors",
                side === s
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground",
              )}
            >
              {s}
            </button>
          ))}
        </div>
        <Badge variant="muted" className="text-[10px]">
          Simulated
        </Badge>
      </div>

      {/* Phone frame */}
      <div className="rounded-[2rem] border-4 border-foreground/80 bg-background p-2 shadow-xl">
        <div className="mx-auto mb-1 h-1 w-12 rounded-full bg-foreground/20" />
        <div className="flex h-[360px] flex-col rounded-[1.4rem] bg-muted/40">
          <div className="border-b border-border px-3 py-2 text-center text-xs font-medium">
            {contact}
          </div>
          <div className="flex flex-1 flex-col justify-end gap-2 overflow-y-auto p-3">
            <AnimatePresence initial={false}>
              {messages.length === 0 ? (
                <p className="text-center text-xs text-muted-foreground">
                  Texts will appear here as the call progresses.
                </p>
              ) : (
                messages.map((m) => (
                  <motion.div
                    key={m.id}
                    initial={{ opacity: 0, y: 8, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    className="max-w-[85%] self-start rounded-2xl rounded-bl-sm bg-primary px-3 py-2 text-sm text-primary-foreground"
                  >
                    {m.text}
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
