import { Link } from "react-router-dom";
import { PhoneCall } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LIVE_CALL_HREF } from "@/components/marketing/constants";

export function TryLiveStrip() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <div className="flex flex-col items-center justify-between gap-4 rounded-2xl border border-border bg-card p-6 sm:flex-row">
        <p className="text-lg font-semibold tracking-tight">
          Hear it answer a call, right now.
        </p>
        <Button asChild variant="outline">
          <Link to={LIVE_CALL_HREF}>
            <PhoneCall className="size-4" /> Try the live call
          </Link>
        </Button>
      </div>
    </section>
  );
}
