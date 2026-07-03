import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { getGraph, type MemoryGraphData } from "@/lib/api";

const TYPE_COLOR: Record<string, string> = {
  Realtor: "#7c3aed",
  Listing: "#2563eb",
  Neighbourhood: "#059669",
  Buyer: "#ea580c",
  Showing: "#d97706",
};

// The buyer + listing memory lives in Cognee (Neo4j graph + pgvector). This renders the
// realtor's own subgraph and re-fetches every 10s so it visibly grows as calls happen.
export function MemoryGraph() {
  const [data, setData] = useState<MemoryGraphData>({ nodes: [], edges: [] });
  const wrap = useRef<HTMLDivElement>(null);
  // Track both dimensions so the canvas fills its column and stands taller as the hero on wide
  // screens, while staying compact on a phone.
  const [size, setSize] = useState({ width: 600, height: 420 });

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function tick() {
      try {
        const d = await getGraph();
        if (active) setData(d);
      } catch {
        // ignore transient errors while polling
      } finally {
        if (active) timer = setTimeout(() => void tick(), 10000);
      }
    }
    void tick();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (!wrap.current) return;
    const ro = new ResizeObserver(([e]) => {
      const w = e.contentRect.width;
      setSize({ width: w, height: w < 640 ? 300 : 420 });
    });
    ro.observe(wrap.current);
    return () => ro.disconnect();
  }, []);

  const graph = useMemo(
    () => ({
      nodes: data.nodes.map((n) => ({ id: n.id, name: `${n.type}: ${n.label}`, type: n.type })),
      links: data.edges.map((e) => ({ source: e.source, target: e.target })),
    }),
    [data],
  );

  return (
    <div ref={wrap} className="min-h-[300px] sm:min-h-[420px]">
      {data.nodes.length === 0 ? (
        <p className="py-16 text-center text-sm text-muted-foreground">
          Your memory graph is empty. Make a call to watch Realtor, Listings, Buyers, and
          Neighbourhoods connect.
        </p>
      ) : (
        <ForceGraph2D
          graphData={graph}
          width={size.width}
          height={size.height}
          nodeRelSize={5}
          nodeColor={(n) => TYPE_COLOR[(n as { type: string }).type] ?? "#64748b"}
          nodeLabel="name"
          linkColor={() => "#cbd5e1"}
          linkDirectionalParticles={1}
        />
      )}
    </div>
  );
}
