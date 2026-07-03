// frontend/src/components/app/memory-section.tsx
import { useEffect, useState } from "react";
import { getInsights, type Insight } from "@/lib/api";
import { MemoryGraph } from "@/components/memory-graph";
import { Card, CardContent } from "@/components/ui/card";

// Node-type legend. Colors MUST match TYPE_COLOR in components/memory-graph.tsx.
const LEGEND = [
  { label: "Realtor", color: "#7c3aed" },
  { label: "Listing", color: "#2563eb" },
  { label: "Neighbourhood", color: "#059669" },
  { label: "Buyer", color: "#ea580c" },
  { label: "Showing", color: "#d97706" },
];

// The Cognee chapter of the Overview story: the live memory graph plus market insights.
export function MemorySection() {
  const [insights, setInsights] = useState<Insight[]>([]);

  useEffect(() => {
    let active = true;
    getInsights()
      .then((i) => active && setInsights(i))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-3 pt-6">
          <p className="text-sm text-muted-foreground">
            Every realtor, listing, neighbourhood, buyer, and showing is a node in a Cognee
            graph. Watch it grow as calls happen.
          </p>
          <div className="flex flex-wrap gap-3">
            {LEGEND.map((l) => (
              <span
                key={l.label}
                className="flex items-center gap-1.5 text-xs text-muted-foreground"
              >
                <span
                  className="size-2.5 rounded-full"
                  style={{ backgroundColor: l.color }}
                />
                {l.label}
              </span>
            ))}
          </div>
          <MemoryGraph />
        </CardContent>
      </Card>

      {insights.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {insights.map((i) => (
            <Card key={i.title + i.body}>
              <CardContent className="pt-6">
                <div className="text-sm font-medium">{i.title}</div>
                <div className="text-sm text-muted-foreground">{i.body}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
