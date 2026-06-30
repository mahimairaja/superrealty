import { Link } from "react-router-dom";

export default function Hub() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-semibold">RealtyRecall</h1>
      <p className="text-muted-foreground max-w-md text-center">
        An always-on voice assistant for solo realtors. It answers in your name, qualifies
        buyers, recommends your homes, and books showings around the clock, and it remembers
        every buyer across calls.
      </p>
      <nav className="flex flex-wrap gap-4 justify-center">
        <Link className="underline" to="/call">
          Talk to the assistant
        </Link>
        <Link className="underline" to="/onboard">
          Connect listings
        </Link>
        <Link className="underline" to="/pipeline">
          Pipeline
        </Link>
      </nav>
    </main>
  );
}
