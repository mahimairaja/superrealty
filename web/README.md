# Super Realty landing site

Astro site (Cloudflare) for superrealty.mahimai.ca. Brand-coherent with mahimai.ca.

## Develop

```bash
cd web
pnpm install
cp .env.example .env      # add PUBLIC_POSTHOG_KEY when ready
pnpm dev
```

## Build and deploy

```bash
pnpm build                # astro build -> dist/ (Cloudflare worker)
pnpm deploy               # wrangler deploy
```

Point superrealty.mahimai.ca at the Cloudflare Worker in the dashboard. The
favicons and OG image under public/ are placeholders; replace with branded art.
