import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { Building2, CalendarCheck, PhoneCall } from "lucide-react";
import {
  getLiveListings,
  getPipeline,
  type PipelineResponse,
} from "@/lib/api";
import { CallLinkCard } from "@/components/app/call-link-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
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

export default function Overview() {
  const { user } = useUser();
  const [listings, setListings] = useState(0);
  const [pipeline, setPipeline] = useState<PipelineResponse>({
    bookings: [],
    calls: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      getLiveListings()
        .then((l) => active && setListings(l.length))
        .catch(() => {}),
      getPipeline()
        .then((p) => active && setPipeline(p))
        .catch(() => {}),
    ]).finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const stats = [
    { icon: Building2, label: "Listings", value: listings, to: "/listings" },
    { icon: PhoneCall, label: "Calls", value: pipeline.calls.length, to: "/pipeline" },
    {
      icon: CalendarCheck,
      label: "Bookings",
      value: pipeline.bookings.length,
      to: "/pipeline",
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">
          {greeting()}
          {user?.firstName ? `, ${user.firstName}` : ""}
        </h2>
        <p className="text-sm text-muted-foreground">
          Here is what your always-on assistant has been up to.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {stats.map((s) => (
          <Link key={s.label} to={s.to}>
            <Card className="gap-2 py-5 transition-shadow hover:shadow-md">
              <CardContent className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {s.label}
                  </div>
                  <div className="text-3xl font-semibold tabular-nums">
                    {loading ? "—" : s.value}
                  </div>
                </div>
                <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <s.icon className="size-5" />
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <CallLinkCard />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent activity</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Loading...
            </p>
          ) : pipeline.calls.length === 0 && pipeline.bookings.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No calls yet. Share your call link and your assistant takes it
              from there.
            </p>
          ) : (
            <>
              {pipeline.bookings.slice(0, 3).map((b) => (
                <div
                  key={`b-${b.id ?? b.address}`}
                  className="flex items-center justify-between gap-3 border-b border-border py-2.5 last:border-0"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">
                      Showing · {b.address ?? "home"}
                    </div>
                    <div className="text-xs tabular-nums text-muted-foreground">
                      {fmt(b.start_utc)}
                    </div>
                  </div>
                  <Badge variant="success">Booking</Badge>
                </div>
              ))}
              {pipeline.calls.slice(0, 4).map((c) => (
                <div
                  key={`c-${c.id ?? c.room_name}`}
                  className="flex items-center justify-between gap-3 border-b border-border py-2.5 last:border-0"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">
                      Call {c.buyer_phone ? `· ${c.buyer_phone}` : ""}
                    </div>
                    <div className="text-xs tabular-nums text-muted-foreground">
                      {fmt(c.ended_at)}
                    </div>
                  </div>
                  <Badge variant="info">{c.outcome ?? "call"}</Badge>
                </div>
              ))}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
