# Skill ranker data (M1)

Public identifiers and freshly fetched measurements for the 20 seed skills. Pages are not generated here. Nothing in this directory is uploaded with `site/`.

The collector reads public HTTPS pages and the GitHub REST API. It does not call a model API, does not use a paid key, and does not log into a site. A missing or unfetchable field is `null`, with `reason` and the URL that was tried.

`GITHUB_TOKEN` (or `GH_TOKEN`) is optional. When it is set, it is sent only to `api.github.com`. Without it, the collector uses the unauthenticated GitHub API.

## Rerun

From the repository root:

```bash
python3 -m pip install --user jsonschema
python3 scripts/skills/collect.py
python3 scripts/skills/validate.py
```

`collect.py` rewrites `data/skills/skills.json`. `validate.py` checks that file against `data/skills/schema.json` and exits non-zero if any collected value lacks an `https` `url` or an ISO 8601 `fetched_at`. It also prints `null_fields` per skill.

The seed list is `scripts/skills/seed.json`. `folder` is a hint for the skill directory; the collector still requires a public `SKILL.md` whose frontmatter `name` matches the slug.
