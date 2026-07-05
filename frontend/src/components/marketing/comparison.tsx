const COLS = ["RealtyRecall", "Aira", "Callium", "Structurely"];

// Each row: label plus one cell per column in COLS order. `star` highlights the
// differentiator row. Roadmap items are labelled honestly, never claimed.
const ROWS: { label: string; cells: string[]; star?: boolean }[] = [
  { label: "Real-estate native", cells: ["Yes", "No", "Yes", "Yes"] },
  { label: "Answers in your voice", cells: ["Yes", "Partial", "Yes", "Limited"] },
  {
    label: "Remembers buyers + proactive match",
    cells: ["Yes", "No", "No", "No"],
    star: true,
  },
  {
    label: "Setup fee",
    cells: ["$0", "$0 (10 to 40 hrs to tune)", "Setup fee", "$2,000 to $2,500"],
  },
  {
    label: "Time to live",
    cells: ["Minutes", "Hours to tune", "About 2 weeks", "Team onboarding"],
  },
  {
    label: "Monthly",
    cells: ["From $297", "$24.95 to $159.95 per-call", "Custom", "$499 plus"],
  },
  { label: "Books showings", cells: ["Yes", "Yes", "Yes", "Yes"] },
  {
    label: "Autonomous follow-up + CRM sync",
    cells: ["Coming soon", "Partial", "Partial", "Native"],
  },
];

export function Comparison() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
        How RealtyRecall compares.
      </h2>
      <div className="mt-8 overflow-x-auto rounded-xl border border-border">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-border bg-card">
              <th scope="col" className="p-3 text-left font-medium">
                Feature
              </th>
              {COLS.map((c) => (
                <th
                  key={c}
                  scope="col"
                  className={
                    c === "RealtyRecall"
                      ? "p-3 text-left font-semibold text-primary"
                      : "p-3 text-left font-medium text-muted-foreground"
                  }
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr
                key={r.label}
                className={r.star ? "border-t border-border bg-accent/40" : "border-t border-border"}
              >
                <th scope="row" className="p-3 text-left font-normal">
                  {r.label}
                </th>
                {r.cells.map((cell, i) => (
                  <td
                    key={COLS[i]}
                    className={
                      i === 0 ? "p-3 font-medium text-foreground" : "p-3 text-muted-foreground"
                    }
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        Competitor details from public pages, mid-2026. Verify current terms before
        relying on them.
      </p>
    </section>
  );
}
