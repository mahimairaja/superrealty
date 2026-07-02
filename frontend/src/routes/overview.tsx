import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { Building2, CalendarCheck, PhoneCall, Sparkles } from "lucide-react";
import {
  getAssistantPersona,
  getLiveListings,
  getPipeline,
  type PipelineResponse,
  type RealtorProfile,
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
  const [persona, setPersona] = useState<RealtorProfile | null>(null);
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
      getAssistantPersona()
        .then((p) => active && setPersona(p))
        .catch(() => {}),
    ]).finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const personaName = persona?.name?.trim();
  const personaAgency = persona?.agency?.trim();
  const introWho = personaName
    ? personaAgency
      ? `${personaName}'s assistant at ${personaAgency}`
      : `${personaName}'s assistant`
    : null;

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

      {!loading && listings === 0 && (
        <Card className="border-primary/30 bg-accent/30">
          <CardContent className="flex flex-col gap-3 py-5">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Getting started
            </div>
            <ol className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground">
                  1
                </span>
                <Link to="/listings" className="font-medium text-primary hover:underline">
                  Connect your listings
                </Link>
                <span className="text-muted-foreground">
                  — paste your site URL, or try our sample site.
                </span>
              </li>
              <li className="flex items-center gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-[11px] font-semibold text-muted-foreground">
                  2
                </span>
                <span className="font-medium">Share your call link</span>
                <span className="text-muted-foreground">
                  — your assistant answers and remembers every caller.
                </span>
              </li>
            </ol>
          </CardContent>
        </Card>
      )}

      <CallLinkCard />

      {introWho && (
        <Card className="border-primary/30 bg-accent/30">
          <CardContent className="flex items-start gap-3 py-5">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="size-5" />
            </span>
            <div className="min-w-0 space-y-1">
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Your assistant
              </div>
              <p className="text-sm">
                On calls, it answers as <strong>{introWho}</strong>
                {persona?.tone ? (
                  <>
                    {" "}
                    in a <span className="text-primary">{persona.tone}</span>{" "}
                    tone
                  </>
                ) : null}
                {persona?.area ? `, serving ${persona.area}` : ""}.
              </p>
              {persona?.tagline && (
                <p className="text-sm italic text-muted-foreground">
                  "{persona.tagline}"
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

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
