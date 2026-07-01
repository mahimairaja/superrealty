import { AnimatePresence, motion } from "motion/react";
import { curatedImage, formatPrice, houseImage } from "@/lib/house-images";
import { listingKey, type Listing } from "@/lib/tool-events";
import { cn } from "@/lib/utils";

export function HouseShortlist({
  matches,
  activeKey,
}: {
  matches: Listing[];
  activeKey: string | null;
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <AnimatePresence initial={false}>
        {matches.map((m, i) => {
          const key = listingKey(m);
          return (
            <motion.div
              key={key || i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i, 6) * 0.06 }}
              className={cn(
                "overflow-hidden rounded-lg border border-border bg-card",
                key && key === activeKey && "ring-2 ring-primary",
              )}
            >
              <img
                src={houseImage(m)}
                alt={m.address ?? "Home"}
                loading="lazy"
                onError={(e) => {
                  const el = e.currentTarget;
                  if (!el.dataset.fb) {
                    el.dataset.fb = "1";
                    el.src = curatedImage(m);
                  }
                }}
                className="h-24 w-full object-cover"
              />
              <div className="space-y-0.5 p-2.5">
                <p className="text-sm font-semibold text-primary tabular-nums">
                  {formatPrice(m.price)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {[m.beds != null && `${m.beds} bd`, m.baths != null && `${m.baths} ba`]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                <p className="truncate text-xs">{m.address}</p>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
