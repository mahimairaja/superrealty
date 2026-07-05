import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { StartFreeButton } from "@/components/marketing/start-free-button";
import { LIVE_CALL_HREF, TRUST_CHIPS } from "@/components/marketing/constants";

export function FinalCta() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
      <div className="flex flex-col items-center gap-6 rounded-2xl border border-border bg-accent/30 px-6 py-14 text-center">
        <h2 className="max-w-xl text-3xl font-semibold tracking-tight">
          Stop losing leads to voicemail.
        </h2>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <StartFreeButton />
          <Button asChild size="lg" variant="outline">
            <Link to={LIVE_CALL_HREF}>Try the live call</Link>
          </Button>
        </div>
        <ul className="flex flex-wrap justify-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
          {TRUST_CHIPS.map((chip) => (
            <li key={chip}>{chip}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
