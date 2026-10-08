# luckysushi.ai

Source for the public Lucky Sushi site, https://luckysushi.ai. It's plain static HTML and CSS: no build step, no trackers beyond Cloudflare Web Analytics, and no form backend. Sign-ups go to Substack.

| Path | What |
|---|---|
| `site/` | Everything that gets served |
| `scripts/build-pages-upload.py` | Builds the Cloudflare Pages Direct Upload payload from `site/` only |
| `scripts/bust-css.py` | Stamps `?v=<hash>` on stylesheet links after `styles.css` changes |
| `wrangler.toml` | Pages project name + output dir (`./site`) |
| `DEPLOY.md` | How deploys and rollbacks work |

Only site code lives here. Planning material is kept in a separate private repo, so a deploy from this repo can't reach it.

Preview locally: `cd site && python3 -m http.server 8000`.
