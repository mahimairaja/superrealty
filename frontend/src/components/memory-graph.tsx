import { API_BASE } from "@/lib/api";

// The buyer + listing memory lives in Cognee (Neo4j graph + pgvector). A live graph
// visualization (Cognee's visualize_graph HTML, or the Neo4j Browser) can be embedded
// here; for M0 this links out to the graph store rather than embedding it.
export function MemoryGraph() {
  return (
    <div className="flex flex-col gap-2 text-sm text-muted-foreground">
      <p>
        Realtor, Listings, Neighbourhoods, Buyers, and Showings form a living memory graph
        in Cognee. Watch it grow as calls happen.
      </p>
      <p>
        Backend:{" "}
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
          {API_BASE}
        </code>
      </p>
    </div>
  );
}
