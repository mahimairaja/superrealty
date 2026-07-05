// Paraphrased voice-of-customer, never attributed and never quoted as testimonials.
const PAINS = [
  "Leads going to voicemail, or hanging up the second you say your name.",
  "Up at 6am on follow-ups, answering urgent texts at 10pm.",
  "Buyers who ghost after a showing you drove across town for.",
  "You are the marketer, the admin, the receptionist, and the therapist.",
];

export function Pain() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <h2 className="max-w-2xl text-2xl font-semibold tracking-tight sm:text-3xl">
        You cannot be in a showing and on the phone at the same time.
      </h2>
      <ul className="mt-8 grid gap-3 sm:grid-cols-2">
        {PAINS.map((p) => (
          <li
            key={p}
            className="rounded-xl border border-border bg-card px-4 py-3 text-sm text-muted-foreground"
          >
            {p}
          </li>
        ))}
      </ul>
      <p className="mt-8 max-w-2xl text-base text-foreground">
        RealtyRecall takes the receptionist off your plate, so you can set a
        boundary without losing the lead.
      </p>
    </section>
  );
}
