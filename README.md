# luckysushi.ai

Source for the public Lucky Sushi site, https://luckysushi.ai. It's plain static HTML and CSS: no build step, no trackers beyond Cloudflare Web Analytics, and no form backend. Sign-ups go to Substack.

| Path | What |
|---|---|
| `site/` | Everything that gets served |
| `scripts/build-pages-upload.py` | Builds the Cloudflare Pages Direct Upload payload from `site/` only |
| `scripts/bust-css.py` | Stamps `?v=<hash>` on stylesheet links after `styles.css` changes |
| `scripts/skills/` | Skill-ranker collectors (not uploaded) |
| `data/skills/` | Skill-ranker schema and generated JSON (not uploaded) |
| `wrangler.toml` | Pages project name + output dir (`./site`) |
| `DEPLOY.md` | How deploys and rollbacks work |

The deploy directory is `site/`. Skill-ranker data stays outside it, so a Pages upload from `site/` does not include it. Planning material is kept in a separate private repo.

Preview locally: `cd site && python3 -m http.server 8000`.
