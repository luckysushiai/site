# Deploying luckysushi.ai (Cloudflare Pages)

## Setup

| Thing | Value |
|---|---|
| Pages project | `luckysushi-ai`, production branch `main`, **Direct Upload** (no Git integration, no Cloudflare GitHub app) |
| Deploy source | This repo (`luckysushiai/site`), from a clean clone. Since 2026-10-08, nothing else deploys the site. |
| pages.dev URL | https://luckysushi-ai.pages.dev (sends `X-Robots-Tag: noindex` via `_headers`) |
| Custom domains | `luckysushi.ai`, `www.luckysushi.ai` (www 301-redirects to the apex via a zone redirect rule) |
| Files deployed | Everything in `site/` except `_headers`, which is sent as the deployment's headers file |
| Web Analytics | Cloudflare Web Analytics, auto-injected at the edge (the CSP in `site/_headers` allows it) |

Account, zone and ruleset IDs are deliberately left out of this public repo. They're in the private planning repo.

Rules:
- Deploys need Aaron's yes.
- Never touch DNS. The Email Routing MX/TXT records stay as they are.
- Public site files must contain **no email address**. Before each deploy, this should print nothing: `rg -a -i '[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|mailto:' site`.
- After any change to `site/styles.css`, run `python3 scripts/bust-css.py` and commit. Browsers cache `styles.css` for an hour.
- HSTS is `max-age=86400`. Raising it, and HSTS preload, are separate decisions.

## How to deploy

Option A (wrangler, needs a one-time `wrangler login`):
```bash
git clone https://github.com/luckysushiai/site.git && cd site
npx wrangler pages deploy site --project-name=luckysushi-ai --branch=main
```

Option B (Cloudflare connector + curl, the same Direct Upload protocol wrangler uses):
1. From a clean clone, run `python3 scripts/build-pages-upload.py`. It writes `/tmp/lsdeploy/{upload,hashes,manifest}.json` and prints the manifest. It reads `site/` only.
2. Connector: `GET /accounts/{acct}/pages/projects/luckysushi-ai/upload-token` returns a JWT that's valid for 30 minutes and scoped to asset upload for this project.
3. With `Authorization: Bearer <jwt>`, POST to `https://api.cloudflare.com/client/v4/pages/assets/check-missing` (`@hashes.json`), then `/pages/assets/upload` (only the missing ones), then `/pages/assets/upsert-hashes`. Delete the JWT afterward.
4. Connector: `POST /accounts/{acct}/pages/projects/luckysushi-ai/deployments` as multipart with `manifest`, `branch=main`, `commit_hash`, `commit_message`, and `_headers` (contents of `site/_headers`).
5. Verify with `curl -sSI https://luckysushi.ai/`. A deliberate bad path like `/does-not-exist` should return 404.

Rollback: `POST /accounts/{acct}/pages/projects/luckysushi-ai/deployments/{deployment_id}/rollback`.

Optional later (needs Aaron's yes): push-to-deploy. Direct Upload projects can't be switched to Git integration, so that would mean a new Git-connected project plus the Cloudflare GitHub app, then moving the custom domains.

## Deployment history

| When (PT) | Deployment | Source |
|---|---|---|
| 2026-10-08 ~4:08 PM | `14f09757` | `7966512`: footer X link (`https://x.com/luckysushiai`, `rel="me noopener"`) on home, privacy and 404. Uploaded the 3 changed HTML files with a scoped 30-minute upload token, which was deleted afterward. Rollback target: `581bc88c` |
| 2026-10-08 ~2:27 PM | `581bc88c` | `luckysushiai/site` `a6fe85e`, from a clean clone. Same manifest and `_headers` as `96a120ff`; first deploy from this repo. All assets were already uploaded under the same hashes, so no upload token was needed |
| 2026-10-08 ~8:27 AM | `96a120ff` | Pre-split repo. Nav "Lab" goes to `#off-leash-lab` |
| 2026-10-08 ~8:17 AM | `e6588725` | Pre-split repo. Off Leash Lab gets its own section |
| 2026-10-08 ~8:15 AM | `0e52196a` | Pre-split repo. Rename to The Off Leash Lab |
| 2026-10-08 ~8:13 AM | `360b1003` | Pre-split repo. Publish "What we're chewing on" |
| 2026-10-07 ~7:41 PM | `7d9ff51b` | Pre-split repo |
| 2026-10-07 ~6:35 PM | `8c7c8dc3` | Pre-split repo. First production deploy |
