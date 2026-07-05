import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { StartFreeButton } from "@/components/marketing/start-free-button";
import { TRIAL_DAYS } from "@/components/marketing/constants";

const TIERS = [
  {
    name: "Starter",
    price: "$297",
    cadence: "/mo",
    minutes: "500 minutes / mo",
    featured: false,
    features: [
      "24/7 answering in your name",
      "Lead qualification (budget, timeline, area)",
      "Books showings on your calendar",
      "Texts you lead details instantly",
      "Basic CRM and calendar",
    ],
  },
  {
    name: "Pro",
    price: "$597",
    cadence: "/mo",
    minutes: "1,500 minutes / mo",
    featured: true,
    features: [
      "Everything in Starter",
      "Web-lead instant callback",
      "Monthly call-insights report",
      "Full CRM and calendar",
    ],
  },
  {
    name: "Brokerage",
    price: "Custom",
    cadence: "",
    minutes: "Higher volume",
    featured: false,
    features: [
      "Everything in Pro",
      "Multiple agents, numbers, routing",
      "Custom integration",
    ],
  },
];

export function Pricing() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <h2 className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">
        Simple pricing. No setup fee.
      </h2>
      <p className="mt-2 text-center text-sm text-muted-foreground">
        Start free for {TRIAL_DAYS} days. Cancel anytime.
      </p>
      <div className="mt-10 grid gap-4 lg:grid-cols-3">
        {TIERS.map((t) => (
          <Card
            key={t.name}
            className={cn(t.featured && "border-primary shadow-md")}
          >
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">{t.name}</h3>
                {t.featured && (
                  <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">
                    Most popular
                  </span>
                )}
              </div>
              <p>
                <span className="text-3xl font-semibold">{t.price}</span>
                <span className="text-sm text-muted-foreground">{t.cadence}</span>
              </p>
              <p className="text-sm text-muted-foreground">{t.minutes}</p>
              <StartFreeButton size="default" className="w-full" />
              <ul className="flex flex-col gap-2">
                {t.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                    <span className="text-muted-foreground">{f}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
      <p className="mt-6 text-center text-xs text-muted-foreground">
        Overage: $0.25 / $0.20 / $0.15 per minute.
      </p>
      <p className="mt-2 text-center text-sm font-medium text-foreground">
        Structurely: $499/mo plus $2,500 setup. RealtyRecall Pro: $597/mo, $0 setup.
      </p>
    </section>
  );
}
