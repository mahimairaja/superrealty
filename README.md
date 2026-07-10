# Super Realty

**The always-on voice receptionist for solo real estate agents. It answers every call in your name, qualifies the buyer, books the showing, and never forgets a caller.**

Every missed call is a missed commission: buyers dial the agent who answers first, and most calls come in after hours. Super Realty picks up every one, 24/7, in your name and voice, and remembers every buyer across calls.

<p>
  <img src="assets/badges/cognee.svg" height="28" alt="Cognee" />
  <img src="assets/badges/livekit.svg" height="28" alt="LiveKit" />
  <img src="assets/badges/fastapi.svg" height="28" alt="FastAPI" />
  <img src="assets/badges/react.svg" height="28" alt="React" />
  <a href="LICENSE"><img src="assets/badges/license-mit.svg" height="28" alt="MIT License" /></a>
</p>

[Run it](#run-it) · [How it's built](#how-its-built) · [Work with me](#work-with-me)

## What it does

- **Answers in your name and voice.** A voice agent picks up every call, discloses recording, and qualifies budget, timeline, financing, and area. It only ever describes homes you have connected.
- **A team of specialists, not one bot.** Each call is handled by a Concierge that greets and routes, a Property agent that searches and shows homes, and a Scheduling agent that books, handing off in real time. The Super Agents dashboard shows the handoff live.
- **Onboards from one URL.** Paste your website; it extracts your listings and infers your persona (name, agency, area, tone) for you to review.
- **Remembers every buyer, across calls.** Buyers and homes live in a Cognee knowledge graph. A returning caller is greeted by name and picks up where they left off.
- **Books real showings.** It checks your Cal.com calendar and books, with an idempotency key so a retry never double-books.
- **Hands you the lead instantly.** When the call ends it texts the buyer and outcome to your phone, so you follow up while the lead is warm.

## Run it

There is no hosted demo. Run the whole stack yourself in one command:

```bash
git clone https://github.com/mahimairaja/superrealty.git
cd superrealty
make up
```

`make up` bootstraps `.env`, builds and starts everything (Postgres + pgvector, Neo4j, a bundled LiveKit server, backend, agent, frontend), applies migrations, and seeds a demo. Frontend at http://localhost:5173, API docs at http://localhost:8000/docs.

For voice, add `OPENAI_API_KEY` and `DEEPGRAM_API_KEY` to `.env`. To talk to the agent in your terminal, no LiveKit needed:

```bash
docker compose run --rm agent uv run python main.py console
```

Prefer plain Docker? `docker compose up` works too. See `.env.example` for every setting.

## How it's built

One voice agent runs the whole call: identity, listing search, lead capture, booking, and forget are tools on a single agent behind one tenant-scoped API, so the same rules apply whether a buyer speaks or types. Memory is the system of record: listings and buyers live in Cognee's graph and vectors, which is what turns a returning caller into a known buyer instead of a fresh transcript.

**Stack:** LiveKit voice, Deepgram + OpenAI, Cognee memory (Neo4j + pgvector), FastAPI, React 19, Cal.com + Telnyx, multi-tenant, MIT.

## Work with me

**Built by Mahimai.** One developer, end to end: the voice agent, the memory graph, the telephony, the multi-tenant backend, and the UI. I ship production voice agents on an open-source stack. Want one for your business?

- Book a call → [mahimai.ca/contact](https://mahimai.ca/contact)
- Email → contact@mahimai.ca

## License

MIT. You own what you run.
