import { ChevronDown } from "lucide-react";
import { TRIAL_DAYS } from "@/components/marketing/constants";

const FAQS = [
  {
    q: "Does it sound like a robot?",
    a: "No. It speaks in your synthesized voice and knows your actual listings, not a generic script.",
  },
  {
    q: "Where does my data live?",
    a: "Canadian data residency. Each realtor's data is isolated from every other realtor's.",
  },
  {
    q: "Are the calls compliant?",
    a: "Recording disclosure is built in and consent is captured. Any outbound is TCPA-aware.",
  },
  {
    q: "What if it misses a call?",
    a: "Never-Miss promise: if it ever misses a call while live, that month is free.",
  },
  {
    q: "How long does setup take?",
    a: "Minutes, from your listings URL. There is no setup fee.",
  },
  {
    q: "Can I cancel?",
    a: `Yes. The trial is ${TRIAL_DAYS} days and risk-free, and you can cancel anytime.`,
  },
];

export function Faq() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
        Questions solo agents ask.
      </h2>
      <div className="mt-8 flex flex-col gap-2">
        {FAQS.map((f) => (
          <details
            key={f.q}
            className="group rounded-xl border border-border bg-card px-4 py-3"
          >
            <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-medium">
              {f.q}
              <ChevronDown className="size-4 text-muted-foreground transition-transform group-open:rotate-180" />
            </summary>
            <p className="mt-2 text-sm text-muted-foreground">{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
