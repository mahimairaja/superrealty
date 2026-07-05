import { Link } from "react-router-dom";
import { ArrowRight, PhoneCall, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StartFreeButton } from "@/components/marketing/start-free-button";
import { GraphMotif } from "@/components/marketing/graph-motif";
import { LIVE_CALL_HREF, TRIAL_DAYS, TRUST_CHIPS } from "@/components/marketing/constants";

export function Hero() {
  return (
    <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 pt-16 pb-14 sm:px-6 sm:pt-24 lg:grid-cols-2">
      <div className="flex flex-col items-start gap-6">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
          <Sparkles className="size-3.5 text-primary" />
          Always-on voice receptionist with a memory
        </span>
        <h1 className="text-pretty text-4xl font-semibold tracking-tight sm:text-5xl">
          Answer every call in your name.{" "}
          <span className="text-primary">Never forget a buyer.</span>
        </h1>
        <p className="max-w-xl text-base text-muted-foreground sm:text-lg">
          RealtyRecall is the always-on receptionist for solo agents. It picks up
          every call, qualifies the buyer, books the showing, and remembers every
          caller across calls. Live from your website URL in minutes.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <StartFreeButton />
          <Button asChild size="lg" variant="outline">
            <Link to={LIVE_CALL_HREF}>
              <PhoneCall className="size-4" /> Hear it answer a call
            </Link>
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          {TRIAL_DAYS}-day free trial. No setup fee. Live in minutes.
        </p>
        <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
          {TRUST_CHIPS.map((chip) => (
            <li key={chip} className="inline-flex items-center gap-1">
              <ArrowRight className="size-3 text-primary" /> {chip}
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-2xl border border-border bg-card p-6">
        <GraphMotif className="w-full text-primary" />
        <p className="mt-3 text-center text-xs text-muted-foreground">
          Every caller and preference, remembered and matched to your homes.
        </p>
      </div>
    </section>
  );
}
