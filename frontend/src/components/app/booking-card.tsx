import { motion } from "motion/react";
import { CalendarCheck, Clock } from "lucide-react";
import { formatWhen } from "@/lib/format";
import type { BookingData } from "@/lib/tool-events";

export function BookingCard({ booking }: { booking: BookingData }) {
  const confirmed = booking.status === "accepted";
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="rounded-xl border border-primary/30 bg-accent/40 p-4"
    >
      <div className="flex items-center gap-2 text-sm font-semibold">
        <CalendarCheck className="size-4 text-primary" />
        {confirmed ? "Showing booked" : "Showing requested"}
      </div>
      <p className="mt-1 text-sm font-medium">{booking.address ?? "Showing"}</p>
      <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted-foreground">
        <Clock className="size-3.5" />
        {formatWhen(booking.startUtc)}
      </p>
    </motion.div>
  );
}
