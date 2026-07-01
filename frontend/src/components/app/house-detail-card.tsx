import { motion } from "motion/react";
import { curatedImage, formatPrice, houseImage } from "@/lib/house-images";
import type { Listing } from "@/lib/tool-events";

export function HouseDetailCard({ listing }: { listing: Listing }) {
  const specs = [
    listing.beds != null && `${listing.beds} bed`,
    listing.baths != null && `${listing.baths} bath`,
    listing.sqft != null && `${listing.sqft.toLocaleString()} sqft`,
  ].filter(Boolean);

  return (
    <motion.div
      key={listing.code ?? listing.address}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-xl border border-border bg-card"
    >
      <img
        src={houseImage(listing)}
        alt={listing.address ?? "Home"}
        onError={(e) => {
          const el = e.currentTarget;
          if (!el.dataset.fb) {
            el.dataset.fb = "1";
            el.src = curatedImage(listing);
          }
        }}
        className="h-48 w-full object-cover"
      />
      <div className="space-y-1 p-4">
        <p className="text-xl font-semibold text-primary tabular-nums">
          {formatPrice(listing.price)}
        </p>
        <p className="font-medium">{listing.address}</p>
        {specs.length > 0 && (
          <p className="text-sm text-muted-foreground">{specs.join(" · ")}</p>
        )}
        {listing.description && (
          <p className="pt-1 text-sm text-muted-foreground">{listing.description}</p>
        )}
      </div>
    </motion.div>
  );
}
