import { Link2, PhoneCall, Brain } from "lucide-react";

const STEPS = [
  {
    icon: Link2,
    title: "Paste your listings URL",
    body: "Your homes and your brand are read into a memory graph in under a minute.",
  },
  {
    icon: PhoneCall,
    title: "Get your buyer line",
    body: "Share it, embed it, or forward your number. It answers 24/7 in your voice.",
  },
  {
    icon: Brain,
    title: "It remembers",
    body: "Every caller and preference, matched to new listings automatically.",
  },
];

export function HowItWorks() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <h2 className="max-w-2xl text-2xl font-semibold tracking-tight sm:text-3xl">
        Live from your website URL. In minutes, not weeks.
      </h2>
      <ol className="mt-10 grid gap-4 sm:grid-cols-3">
        {STEPS.map((s, i) => (
          <li key={s.title} className="rounded-xl border border-border bg-card p-5">
            <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <s.icon className="size-5" />
            </span>
            <h3 className="mt-4 text-base font-semibold tracking-tight">
              {i + 1}. {s.title}
            </h3>
            <p className="mt-2 text-sm text-muted-foreground">{s.body}</p>
          </li>
        ))}
      </ol>
      <p className="mt-8 text-base font-medium text-foreground">
        No setup fee. No two-week deployment. No data handoff.
      </p>
    </section>
  );
}
