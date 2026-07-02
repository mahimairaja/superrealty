import { useEffect, useState } from "react";
import { CalendarCheck, PhoneCall, Users } from "lucide-react";
import { getInsights, getPipeline, type Insight, type PipelineResponse } from "@/lib/api";
import { MatchCard } from "@/components/match-card";
import { MemoryGraph } from "@/components/memory-graph";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Variant = "success" | "info" | "warning" | "muted";

function callBadge(outcome?: string | null): { variant: Variant; label: string } {
  switch (outcome) {
    case "booked":
      return { variant: "success", label: "Booked" };
    case "completed":
      return { variant: "info", label: "Completed" };
    case "abandoned":
      return { variant: "warning", label: "Abandoned" };
    default:
      return { variant: "muted", label: outcome ?? "In progress" };
  }
}

function bookingBadge(status: string): { variant: Variant; label: string } {
  return status === "accepted"
    ? { variant: "success", label: "Accepted" }
    : { variant: "muted", label: status };
}

function fmt(iso?: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function Pipeline() {
  const [data, setData] = useState<PipelineResponse>({ bookings: [], calls: [] });
  const [insights, setInsights] = useState<Insight[]>([]);
  useEffect(() => {
    getInsights().then(setInsights).catch(() => {});
  }, []);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    // Self-scheduling poll: the next request is only armed after the current one settles, so
    // slow responses never pile up against the (graph-backed) pipeline endpoint.
    async function tick() {
      try {
        const d = await getPipeline();
        if (active) setData(d);
      } catch {
        // ignore transient errors while polling
      } finally {
        if (active) timer = setTimeout(() => void tick(), 4000);
      }
    }
    void tick();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, []);

  const leads = new Set(
    [
      ...data.calls.map((c) => c.buyer_phone),
      ...data.bookings.map((b) => b.phone),
    ].filter(Boolean),
  ).size;

  const stats = [
    { icon: CalendarCheck, label: "Bookings", value: data.bookings.length },
    { icon: PhoneCall, label: "Calls", value: data.calls.length },
    { icon: Users, label: "Buyers", value: leads },
  ];

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted-foreground">
        Bookings and calls, hydrated live from memory.
      </p>

      <div className="grid gap-4 sm:grid-cols-3">
        {stats.map((s) => (
          <Card key={s.label} className="gap-2 py-5">
            <CardContent className="flex items-center justify-between">
              <div className="space-y-1">
                <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {s.label}
                </div>
                <div className="text-3xl font-semibold tabular-nums">
                  {s.value}
                </div>
              </div>
              <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <s.icon className="size-5" />
              </span>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent bookings</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col">
            {data.bookings.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No bookings yet.
              </p>
            ) : (
              data.bookings.map((b) => {
                const badge = bookingBadge(b.status);
                return (
                  <div
                    key={b.id ?? b.address}
                    className="flex items-center justify-between gap-3 border-b border-border py-2.5 last:border-0"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {b.address ?? "Showing"}
                      </div>
                      <div className="text-xs tabular-nums text-muted-foreground">
                        {fmt(b.start_utc)}
                      </div>
                    </div>
                    <Badge variant={badge.variant}>{badge.label}</Badge>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent calls</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col">
            {data.calls.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No calls yet.
              </p>
            ) : (
              data.calls.map((c) => {
                const badge = callBadge(c.outcome);
                return (
                  <div
                    key={c.id ?? c.room_name}
                    className="flex items-center justify-between gap-3 border-b border-border py-2.5 last:border-0"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {c.room_name}
                      </div>
                      {c.buyer_phone && (
                        <div className="font-mono text-xs tabular-nums text-muted-foreground">
                          {c.buyer_phone}
                        </div>
                      )}
                    </div>
                    <Badge variant={badge.variant}>{badge.label}</Badge>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      <MatchCard />

      {insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Market insights</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            {insights.map((i) => (
              <div key={i.title}>
                <div className="font-medium">{i.title}</div>
                <div className="text-muted-foreground">{i.body}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Memory</CardTitle>
        </CardHeader>
        <CardContent>
          <MemoryGraph />
        </CardContent>
      </Card>
    </div>
  );
}
