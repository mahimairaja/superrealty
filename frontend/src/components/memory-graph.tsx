import { API_BASE } from "@/lib/api";

// The buyer + listing memory lives in Cognee (Neo4j graph + pgvector). A live graph
// visualization (Cognee's visualize_graph HTML, or the Neo4j Browser) can be embedded
// here; for M0 this links out to the graph store rather than embedding it.
export function MemoryGraph() {
  return (
    <div className="border rounded p-4 text-sm text-muted-foreground flex flex-col gap-2">
      <p>
        Realtor, Listings, Neighbourhoods, Buyers, and Showings form a living memory graph
        in Cognee. Watch it grow as calls happen.
      </p>
      <p>
        Backend: <code>{API_BASE}</code>
      </p>
    </div>
  );
}
