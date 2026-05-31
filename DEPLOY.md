# Deployment Guide

## Site overview

- **Framework:** Astro (static output)
- **Build output:** `dist/` directory
- **Build command:** `npm run build`
- **Publish directory:** `dist`

## Prerequisites

```
node >= 18
npm >= 9
```

Dependencies install with `npm install`.

## Build

```bash
cd bullitt-site
npm install
npm run build
# dist/ is ready to deploy
```

## Regenerating the 3D model

If you need to regenerate `public/assets/3d/bullitt-cargo.glb`:

```bash
# Requires numpy
uv run --with numpy python3 generate_model.py
# or: pip install numpy && python3 generate_model.py
```

## Deployment options

### Option A: Netlify (recommended)

1. Create a Netlify account at netlify.com
2. Install CLI: `npm install -g netlify-cli`
3. Authenticate: `netlify login`
4. From the `bullitt-site/` directory:
   ```bash
   netlify deploy --prod --dir dist
   ```
   Or link to a Git repo and enable auto-deploy on push.

### Option B: Cloudflare Pages

1. Install Wrangler: `npm install -g wrangler`
2. Authenticate: `wrangler login`
3. Deploy:
   ```bash
   wrangler pages deploy dist --project-name bullitt-site
   ```
   First-time deploy creates the project. Subsequent deploys update it.
   Note: Set `CLOUDFLARE_ACCOUNT_ID` env var before deploying.

### Option C: Coolify (self-hosted)

1. Push this repo to a GitHub/Gitea repository.
2. In Coolify, create a new application → Static site.
3. Build command: `npm run build`
4. Publish directory: `dist`
5. Connect to your repo and deploy.

### Option D: Surge

```bash
npm install -g surge
cd bullitt-site
npm run build
surge dist bullitt-cargo-bike.surge.sh
```

## Environment variables

None required for the static build. The site is fully static — no server-side env vars needed.

## Sitemap / robots.txt

- `robots.txt` is at `public/robots.txt` — update the `Sitemap:` URL to match your domain.
- `sitemap.xml` is generated at `/sitemap.xml` — update the `base` URL in `src/pages/sitemap.xml.astro`.

## Outstanding issues (tracked)

- [ ] GLB model path error on customiser page when running `npm run dev` without a local HTTP server — use `npm run preview` or serve `dist/` instead.
- [ ] Gallery images are placeholder divs — actual image files require downloading from source URLs in `src/data/gallery.json`. Run `content/gallery/IMAGE_OPTIMIZATION.md` script (from task t_bab2af68 content) to download and optimise.
- [ ] Sitemap `base` URL is hardcoded to `https://bullitt.pages.dev` — update before deploying to a custom domain.
- [ ] Wheelbase, chainstay, and cargo inner length remain unconfirmed — physical measurement or dealer inquiry needed.
