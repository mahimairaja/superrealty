// frontend/src/routes/overview.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { Building2, CalendarCheck, PhoneCall, Sparkles, Users } from "lucide-react";
import {
  getAssistantPersona,
  getBuyers,
  getLiveListings,
  getPipeline,
  type PipelineResponse,
  type RealtorProfile,
} from "@/lib/api";
import { CallLinkCard } from "@/components/app/call-link-card";
import { UsageWidget } from "@/components/app/usage-widget";
import { MatchCard } from "@/components/match-card";
import { MemorySection } from "@/components/app/memory-section";
import { StorySection } from "@/components/app/story-section";
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

const STEPS = [
  { n: 1, label: "Connect your listings", hint: "Paste your site URL, or try our sample site." },
  { n: 2, label: "Share your call link", hint: "Your assistant answers every call." },
  { n: 3, label: "It remembers", hint: "Every caller and home lands in your memory graph." },
];

export default function Overview() {
  const { user } = useUser();
  const [listings, setListings] = useState(0);
  const [buyers, setBuyers] = useState(0);
  const [pipeline, setPipeline] = useState<PipelineResponse>({ bookings: [], calls: [] });
  const [persona, setPersona] = useState<RealtorProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      getLiveListings().then((l) => active && setListings(l.length)).catch(() => {}),
      getBuyers().then((b) => active && setBuyers(b.length)).catch(() => {}),
      getPipeline().then((p) => active && setPipeline(p)).catch(() => {}),
      getAssistantPersona().then((p) => active && setPersona(p)).catch(() => {}),
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
    { icon: Building2, label: "Listings", value: listings },
    { icon: PhoneCall, label: "Calls", value: pipeline.calls.length },
    { icon: CalendarCheck, label: "Bookings", value: pipeline.bookings.length },
  ];

  return (
    <div className="flex flex-col gap-8 sm:gap-10">
      {/* 1. What it is */}
      <StorySection
        title={`${greeting()}${user?.firstName ? `, ${user.firstName}` : ""}`}
        subtitle="RealtyRecall is an always-on AI receptionist for solo realtors. It answers every call, remembers every caller, and books showings."
      >
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
                      {" "}in a <span className="text-primary">{persona.tone}</span> tone
                    </>
                  ) : null}
                  {persona?.area ? `, serving ${persona.area}` : ""}.
                </p>
                {persona?.tagline && (
                  <p className="text-sm italic text-muted-foreground">"{persona.tagline}"</p>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-3 sm:grid-cols-3">
          {STEPS.map((s) => (
            <Card key={s.n}>
              <CardContent className="flex items-start gap-3 py-4">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                  {s.n}
                </span>
                <div className="space-y-0.5">
                  <div className="text-sm font-medium">{s.label}</div>
                  <div className="text-xs text-muted-foreground">{s.hint}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {!loading && listings === 0 && (
          <Card className="border-primary/30 bg-accent/30">
            <CardContent className="py-4 text-sm">
              <Link to="/listings" className="font-medium text-primary hover:underline">
                Connect your listings
              </Link>{" "}
              <span className="text-muted-foreground">to get started.</span>
            </CardContent>
          </Card>
        )}

        <CallLinkCard />
      </StorySection>

      {/* 2. How it remembers (Cognee) */}
      <StorySection
        title="How it remembers"
        subtitle="Nothing is forgotten between calls. Every caller and home is stored as a connected node."
        cognee
      >
        <MemorySection />
        <Link
          to="/buyers"
          className="flex items-center gap-2 text-sm text-primary hover:underline"
        >
          <Users className="size-4" />
          {loading ? "..." : `${buyers} buyer${buyers === 1 ? "" : "s"} remembered`} - see all
        </Link>
      </StorySection>

      {/* 3. What your assistant has done (proof) */}
      <StorySection
        title="What your assistant has done"
        subtitle="Real calls, bookings, and matches from your memory graph."
      >
        <div className="grid gap-4 sm:grid-cols-3">
          {stats.map((s) => (
            <Card key={s.label} className="gap-2 py-5">
              <CardContent className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {s.label}
                  </div>
                  <div className="text-3xl font-semibold tabular-nums">
                    {loading ? "-" : s.value}
                  </div>
                </div>
                <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <s.icon className="size-5" />
                </span>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="space-y-2">
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Usage this month
          </div>
          <UsageWidget />
        </div>

        <MatchCard />

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent activity</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col">
            {loading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Loading...</p>
            ) : pipeline.calls.length === 0 && pipeline.bookings.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No calls yet. Share your call link and your assistant takes it from there.
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
                        Showing: {b.address ?? "home"}
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
                        Call {c.buyer_phone ? `: ${c.buyer_phone}` : ""}
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
      </StorySection>
    </div>
  );
}
