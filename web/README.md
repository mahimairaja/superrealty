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
pnpm build                # astro build -> dist/ (Cloudflare Worker)
pnpm deploy               # wrangler deploy (requires wrangler login)
```

### Cloudflare setup

1. Run `wrangler login` once to authenticate.
2. After `pnpm deploy`, go to the Cloudflare dashboard and add a Custom Domain
   `superrealty.mahimai.ca` pointing to the Worker.
3. Set `PUBLIC_POSTHOG_KEY` as a build environment variable (Workers and Pages
   dashboard or in your CI environment) before running `pnpm build` in production.

### Placeholders

`public/og-image.png` and the favicons under `public/` are placeholder assets
copied from mahimai.ca. Replace them with branded Super Realty art before the
public launch.
