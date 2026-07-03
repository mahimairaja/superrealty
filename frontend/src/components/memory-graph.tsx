import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D, {
  type ForceGraphMethods,
  type LinkObject,
  type NodeObject,
} from "react-force-graph-2d";
import { getGraph, type MemoryGraphData } from "@/lib/api";
import { useTheme } from "@/lib/use-theme";

const TYPE_COLOR: Record<string, string> = {
  Realtor: "#7c3aed",
  Listing: "#2563eb",
  Neighbourhood: "#059669",
  Buyer: "#ea580c",
  Showing: "#d97706",
};

type GNode = { id: string; name: string; type: string };
type GLink = { source: string; target: string };

// The buyer + listing memory lives in Cognee (Neo4j graph + pgvector). This renders the
// realtor's own subgraph and re-fetches every 10s so it visibly grows as calls happen.
export function MemoryGraph() {
  const { theme } = useTheme();
  const [data, setData] = useState<MemoryGraphData>({ nodes: [], edges: [] });
  const wrap = useRef<HTMLDivElement>(null);
  // Held so onEngineStop can call zoomToFit, scaling the graph to fill and center its canvas.
  const fgRef =
    useRef<ForceGraphMethods<NodeObject<GNode>, LinkObject<GNode, GLink>>>(undefined);
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

  const graph = useMemo(() => {
    // Show only the labeled entity types so the graph matches its legend; Cognee's internal
    // nodes (chunks, summaries) are dropped, and any edge to a dropped node with it.
    const kept = data.nodes.filter((n) => n.type in TYPE_COLOR);
    const ids = new Set(kept.map((n) => n.id));
    return {
      nodes: kept.map((n) => ({ id: n.id, name: `${n.type}: ${n.label}`, type: n.type })),
      links: data.edges
        .filter((e) => ids.has(e.source) && ids.has(e.target))
        .map((e) => ({ source: e.source, target: e.target })),
    };
  }, [data]);

  return (
    <div ref={wrap} className="min-h-[300px] sm:min-h-[420px]">
      {graph.nodes.length === 0 ? (
        <p className="py-16 text-center text-sm text-muted-foreground">
          Your memory graph is empty. Make a call to watch Realtor, Listings, Buyers, and
          Neighbourhoods connect.
        </p>
      ) : (
        <ForceGraph2D
          ref={fgRef}
          graphData={graph}
          width={size.width}
          height={size.height}
          // Transparent so the card's own (theme-aware) background shows through, instead of the
          // canvas painting an opaque light fill that stays bright in dark mode.
          backgroundColor="rgba(0,0,0,0)"
          nodeRelSize={5}
          nodeColor={(n) => TYPE_COLOR[(n as { type: string }).type] ?? "#64748b"}
          nodeLabel="name"
          linkColor={() => (theme === "dark" ? "#475569" : "#cbd5e1")}
          linkDirectionalParticles={1}
          cooldownTicks={80}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 30)}
        />
      )}
    </div>
  );
}
