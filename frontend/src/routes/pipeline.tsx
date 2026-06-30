import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPipeline, type PipelineResponse } from "@/lib/api";
import { MemoryGraph } from "@/components/memory-graph";

export default function Pipeline() {
  const [data, setData] = useState<PipelineResponse>({ bookings: [], calls: [] });

  useEffect(() => {
    let active = true;
    async function tick() {
      try {
        const d = await getPipeline();
        if (active) setData(d);
      } catch {
        // ignore transient errors while polling
      }
    }
    void tick();
    const id = setInterval(() => void tick(), 1000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your pipeline</h1>
        <Link className="underline text-sm" to="/">
          Home
        </Link>
      </div>

      <section>
        <h2 className="font-medium mb-2">Recent bookings</h2>
        {data.bookings.length === 0 ? (
          <p className="text-sm text-muted-foreground">No bookings yet.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {data.bookings.map((b) => (
              <li key={b.id ?? b.address} className="text-sm">
                {b.address ?? "home"} — {b.status}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="font-medium mb-2">Recent calls</h2>
        {data.calls.length === 0 ? (
          <p className="text-sm text-muted-foreground">No calls yet.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {data.calls.map((c) => (
              <li key={c.id ?? c.room_name} className="text-sm">
                {c.room_name} — {c.outcome ?? "in progress"}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="font-medium mb-2">Memory</h2>
        <MemoryGraph />
      </section>
    </main>
  );
}
