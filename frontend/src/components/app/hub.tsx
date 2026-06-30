import { Link } from "react-router-dom";
import {
  ArrowRight,
  CalendarCheck,
  PhoneCall,
  Sparkles,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Upload,
    title: "Connect your listings",
    body: "Paste a listings page or upload a file. Your homes are read into a memory graph in under a minute.",
    to: "/onboard",
    cta: "Connect listings",
  },
  {
    icon: PhoneCall,
    title: "Answer every call",
    body: "A voice assistant picks up in your name, qualifies the buyer, and recommends the homes that fit.",
    to: "/call",
    cta: "Talk to the assistant",
  },
  {
    icon: CalendarCheck,
    title: "Never lose a lead",
    body: "It books showings, texts you the lead, and remembers every buyer across calls.",
    to: "/pipeline",
    cta: "View pipeline",
  },
];

export default function Hub() {
  return (
    <main className="mx-auto max-w-6xl px-4 sm:px-6">
      <section className="flex flex-col items-center gap-6 pt-16 pb-14 text-center sm:pt-24">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
          <Sparkles className="size-3.5 text-primary" />
          Always-on voice receptionist with a memory
        </span>
        <h1 className="max-w-3xl text-pretty text-4xl font-semibold tracking-tight sm:text-5xl">
          Answer every call in your name, and{" "}
          <span className="text-primary">never forget a buyer</span>.
        </h1>
        <p className="max-w-xl text-base text-muted-foreground sm:text-lg">
          RealtyRecall qualifies buyers, recommends your homes, and books
          showings around the clock, then remembers every caller across calls.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg">
            <Link to="/call">
              Talk to the assistant <ArrowRight />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/onboard">Connect listings</Link>
          </Button>
        </div>
      </section>

      <section className="grid gap-4 pb-20 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <Card key={f.title} className="gap-4 transition-shadow hover:shadow-md">
            <CardContent className="flex flex-col gap-3">
              <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <f.icon className="size-5" />
              </span>
              <h3 className="text-base font-semibold tracking-tight">
                {f.title}
              </h3>
              <p className="text-sm text-muted-foreground">{f.body}</p>
              <Link
                to={f.to}
                className="mt-1 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
              >
                {f.cta} <ArrowRight className="size-3.5" />
              </Link>
            </CardContent>
          </Card>
        ))}
      </section>
    </main>
  );
}
