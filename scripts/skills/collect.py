#!/usr/bin/env python3
"""Collect public skill-ranker fields for the 20 seed skills.

Reads scripts/skills/seed.json and writes data/skills/skills.json.
Uses public HTTPS pages and the GitHub REST API only. No model APIs,
no paid keys, and no authenticated third-party accounts.

If GITHUB_TOKEN or GH_TOKEN is set, it is sent only to api.github.com.
Otherwise the unauthenticated API is used.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "scripts" / "skills" / "seed.json"
OUT_PATH = ROOT / "data" / "skills" / "skills.json"

USER_AGENT = "luckysushi-skill-ranker/m1 (+https://github.com/luckysushiai/site)"
CTX = ssl.create_default_context()

THIRD_PARTY_KEYS = (
    "skillzbench",
    "driftproof",
    "happycapy",
    "edge",
    "tessl",
    "openskilleval",
    "swe_skills_bench",
)
SOURCE_NAMES = {
    "skillzbench": "SkillzBench",
    "driftproof": "Driftproof",
    "happycapy": "Happycapy",
    "edge": "Edge",
    "tessl": "Tessl",
    "openskilleval": "OpenSkillEval",
    "swe_skills_bench": "SWE-Skills-Bench",
}

# Display names on Happycapy bylines, mapped to GitHub owner logins.
HAPPYCAPY_OWNERS = {
    "anthropic": "anthropics",
    "anthropics": "anthropics",
    "leonxlnx": "leonxlnx",
    "vercel": "vercel-labs",
    "vercel labs": "vercel-labs",
    "nextlevelbuilder": "nextlevelbuilder",
    "superdesigndev": "superdesigndev",
    "pbakaus": "pbakaus",
    "emil kowalski": "emilkowalski",
    "emilkowalski": "emilkowalski",
    "matt pocock": "mattpocock",
    "mattpocock": "mattpocock",
    "obra": "obra",
    "addy osmani": "addyosmani",
    "addyosmani": "addyosmani",
    "hugo he": "hugohe3",
    "hugohe3": "hugohe3",
    "zara zhang": "zarazhangrui",
    "zarazhangrui": "zarazhangrui",
    "corey haines": "coreyhaines31",
    "coreyhaines31": "coreyhaines31",
}

OPEN_QUESTIONS: list[str] = []
_SEEN_QUESTIONS: set[str] = set()


def note_open(question: str) -> None:
    if question not in _SEEN_QUESTIONS:
        _SEEN_QUESTIONS.add(question)
        OPEN_QUESTIONS.append(question)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sourced(value, url: str, fetched_at: str, reason: str | None = None) -> dict:
    row = {"value": value, "url": url, "fetched_at": fetched_at}
    if value is None:
        row["reason"] = reason or "unfetchable"
    elif reason:
        row["reason"] = reason
    return row


def measurement(source: str, metric, value, model, url: str, fetched_at: str, reason: str | None = None) -> dict:
    row = {
        "source": source,
        "metric": metric,
        "value": value,
        "model": model,
        "url": url,
        "fetched_at": fetched_at,
    }
    if value is None:
        row["reason"] = reason or "unfetchable"
    elif reason:
        row["reason"] = reason
    return row


def missing(source_key: str, url: str, fetched_at: str, reason: str) -> list[dict]:
    return [measurement(SOURCE_NAMES[source_key], None, None, None, url, fetched_at, reason)]


class Http:
    def __init__(self) -> None:
        self.github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

    def get(self, url: str, headers: dict | None = None, timeout: int = 45) -> tuple[int, str, str]:
        hdrs = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
        if headers:
            hdrs.update(headers)
        if "api.github.com" in url and self.github_token:
            hdrs["Authorization"] = f"Bearer {self.github_token}"
            hdrs["Accept"] = "application/vnd.github+json"
            hdrs["X-GitHub-Api-Version"] = "2022-11-28"
        elif "api.github.com" in url:
            hdrs["Accept"] = "application/vnd.github+json"
            hdrs["X-GitHub-Api-Version"] = "2022-11-28"
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
                body = resp.read().decode("utf-8", "replace")
                return resp.status, body, resp.geturl()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            return exc.code, body, url
        except Exception as exc:  # noqa: BLE001 - recorded as a null reason
            return 0, str(exc), url


HTTP = Http()


def html_lines(html: str) -> list[str]:
    from html import unescape

    cleaned = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    cleaned = re.sub(r"<style[\s\S]*?</style>", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", "\n", cleaned)
    return [unescape(line).strip() for line in cleaned.splitlines() if unescape(line).strip()]


def strip_tags(fragment: str) -> str:
    from html import unescape

    text = re.sub(r"<[^>]+>", " ", fragment)
    return unescape(re.sub(r"\s+", " ", text)).strip()


def parse_description(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    lines = text[4:end].splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        rest = line[len("description:") :].strip()
        if rest in {">", ">-", ">+", "|", "|-", "|+"}:
            block = []
            for nxt in lines[i + 1 :]:
                if nxt.startswith((" ", "\t")) or nxt == "":
                    block.append(nxt.strip())
                else:
                    break
            desc = " ".join(part for part in block if part)
            return re.sub(r"\s+", " ", desc).strip() or None
        if rest[:1] in {'"', "'"}:
            quote = rest[0]
            buf = rest[1:]
            if buf.endswith(quote) and len(rest) > 1:
                inner = buf[:-1]
            else:
                parts = [buf]
                for nxt in lines[i + 1 :]:
                    if nxt.rstrip().endswith(quote):
                        parts.append(nxt.rstrip()[:-1])
                        break
                    parts.append(nxt)
                inner = " ".join(parts)
            inner = inner.replace('\\"', '"').replace("\\n", " ")
            return re.sub(r"\s+", " ", inner).strip() or None
        return re.sub(r"\s+", " ", rest).strip() or None
    return None


def frontmatter_name(text: str) -> str | None:
    match = re.search(r"(?m)^name:\s*[\"']?([^\"'\n]+)", text)
    return match.group(1).strip() if match else None


def skill_md_candidates(skill: dict) -> list[str]:
    slug = skill["slug"]
    folder = skill.get("folder")
    paths: list[str] = []
    if folder == "":
        paths.append("SKILL.md")
    elif folder:
        paths.append(f"{folder.rstrip('/')}/SKILL.md")
    paths.extend(
        [
            f"skills/{slug}/SKILL.md",
            f"{slug}/SKILL.md",
            f"skills/engineering/{slug}/SKILL.md",
            f"skills/productivity/{slug}/SKILL.md",
            f"skills/misc/{slug}/SKILL.md",
            f".claude/skills/{slug}/SKILL.md",
            "SKILL.md",
        ]
    )
    seen: set[str] = set()
    out = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def raw_url(owner: str, repo: str, ref: str, path: str) -> str:
    safe = urllib.parse.quote(path, safe="/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{safe}"


def read_skill_md(owner: str, repo: str, ref: str, path: str) -> tuple[int, str]:
    status, body, _ = HTTP.get(raw_url(owner, repo, ref, path))
    return status, body


def locate_skill_md(skill: dict, owner: str, repo: str, branch: str) -> tuple[str | None, str | None]:
    """Return (path, text) for the SKILL.md whose frontmatter name matches the slug."""
    for path in skill_md_candidates(skill):
        status, body = read_skill_md(owner, repo, branch, path)
        if status == 200 and frontmatter_name(body) == skill["slug"]:
            return path, body
    status, body, _ = HTTP.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{urllib.parse.quote(branch)}?recursive=1"
    )
    if status != 200:
        return None, None
    try:
        tree = json.loads(body).get("tree") or []
    except json.JSONDecodeError:
        return None, None
    for item in tree:
        path = item.get("path") or ""
        if item.get("type") == "blob" and path.endswith("SKILL.md"):
            status, text = read_skill_md(owner, repo, branch, path)
            if status == 200 and frontmatter_name(text) == skill["slug"]:
                return path, text
    return None, None


REPO_CACHE: dict[str, dict] = {}


def github_repo(owner: str, repo: str) -> tuple[dict | None, str, str]:
    key = f"{owner}/{repo}".lower()
    url = f"https://api.github.com/repos/{owner}/{repo}"
    if key in REPO_CACHE:
        cached = REPO_CACHE[key]
        return cached["data"], cached["url"], cached["fetched_at"]
    fetched_at = now()
    status, body, final = HTTP.get(url)
    if status != 200:
        REPO_CACHE[key] = {"data": None, "url": final, "fetched_at": fetched_at, "status": status, "body": body[:300]}
        return None, final, fetched_at
    data = json.loads(body)
    REPO_CACHE[key] = {"data": data, "url": final, "fetched_at": fetched_at}
    return data, final, fetched_at


def github_last_commit(owner: str, repo: str, folder: str) -> tuple[dict | None, str, str]:
    query = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
    if folder:
        query += "&path=" + urllib.parse.quote(folder, safe="/")
    fetched_at = now()
    status, body, final = HTTP.get(query)
    if status != 200:
        return None, final, fetched_at
    try:
        commits = json.loads(body)
    except json.JSONDecodeError:
        return None, final, fetched_at
    if not commits:
        return None, final, fetched_at
    return commits[0], final, fetched_at


def skills_sh(skill: dict) -> dict:
    owner, repo, slug = skill["owner"], skill["repo"], skill["slug"]
    page = f"https://www.skills.sh/{owner}/{repo}/{slug}"
    fetched_at = now()
    status, html, final = HTTP.get(page)
    app = None
    if status == 200:
        for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("@type") == "SoftwareApplication":
                app = data
                break
    canon = final
    canon_match = re.search(r'<link rel="canonical" href="([^"]+)"', html or "")
    if canon_match:
        canon = canon_match.group(1)
    installs_url = canon if status == 200 else page
    if status != 200 or app is None or app.get("name") != slug:
        reason = (
            f"HTTP {status} from {page}"
            if status != 200
            else "public page has no SoftwareApplication record for this slug"
        )
        installs = sourced(None, installs_url, fetched_at, reason)
        page_owner, page_repo = owner, repo
    else:
        stat = app.get("interactionStatistic") or {}
        count = stat.get("userInteractionCount")
        if isinstance(count, int):
            installs = sourced(count, installs_url, fetched_at)
        else:
            installs = sourced(None, installs_url, fetched_at, "SoftwareApplication record has no install count")
        parts = urllib.parse.urlparse(canon).path.strip("/").split("/")
        page_owner, page_repo = (parts[0], parts[1]) if len(parts) >= 2 else (owner, repo)

    audit_url = f"https://skills.sh/api/v1/skills/audit/{page_owner}/{page_repo}/{slug}"
    audit_fetched = now()
    audit_status, audit_body, audit_final = HTTP.get(audit_url, headers={"Accept": "application/json"})
    audits = {}
    providers = {}
    if audit_status == 200:
        try:
            payload = json.loads(audit_body)
            for item in payload.get("audits") or []:
                key = (item.get("slug") or "").lower()
                providers[key] = item
        except json.JSONDecodeError:
            providers = {}
    elif audit_status in {401, 403}:
        note_open(
            "skills.sh audit API returned "
            f"HTTP {audit_status} for {audit_url}. No paid key was used."
        )
    for key, slug_name, label in (
        ("gen", "agent-trust-hub", "Gen"),
        ("snyk", "snyk", "Snyk"),
        ("socket", "socket", "Socket"),
    ):
        if audit_status != 200:
            audits[key] = sourced(
                None,
                audit_final,
                audit_fetched,
                f"audit API HTTP {audit_status} for {label}",
            )
            continue
        item = providers.get(slug_name)
        if not item:
            audits[key] = sourced(
                None,
                audit_final,
                audit_fetched,
                f"{label} is not in the public audit response",
            )
            continue
        value = {"status": item.get("status"), "summary": item.get("summary")}
        if item.get("riskLevel") is not None:
            value["risk_level"] = item.get("riskLevel")
        audits[key] = sourced(value, audit_final, audit_fetched)
    return {
        "page_owner": page_owner,
        "page_repo": page_repo,
        "installs": installs,
        "audits": audits,
    }


def github_fields(skill: dict, owner: str, repo: str) -> tuple[dict, str | None, str | None, str | None]:
    """Return github block plus (branch, skill_md_path, claim_text)."""
    repo_data, repo_url, repo_fetched = github_repo(owner, repo)
    if not repo_data:
        cached = REPO_CACHE[f"{owner}/{repo}".lower()]
        status = cached.get("status")
        reason = f"GitHub repo API HTTP {status}"
        if status == 403 and "rate limit" in (cached.get("body") or "").lower():
            reason = "GitHub API rate limit reached before this repo could be read"
            note_open("Unauthenticated GitHub API rate limit was hit. Re-run with GITHUB_TOKEN for the public API only.")
        empty = {
            "stars": sourced(None, repo_url, repo_fetched, reason),
            "skill_folder_last_commit": sourced(None, repo_url, repo_fetched, reason),
        }
        return empty, None, None, None
    login = repo_data["owner"]["login"]
    real_repo = repo_data["name"]
    branch = repo_data.get("default_branch") or "HEAD"
    stars = sourced(repo_data.get("stargazers_count"), repo_url, repo_fetched)
    path, text = locate_skill_md(skill, login, real_repo, branch)
    folder = ""
    if path:
        folder = path.rsplit("/", 1)[0] if "/" in path else ""
    commit, commit_api, commit_fetched = github_last_commit(login, real_repo, folder if path else (skill.get("folder") or ""))
    if commit is None:
        last = sourced(None, commit_api, commit_fetched, "GitHub commits API returned no commit for the skill folder")
        sha = None
    else:
        sha = commit.get("sha")
        date = ((commit.get("commit") or {}).get("committer") or {}).get("date")
        html_url = commit.get("html_url") or commit_api
        if isinstance(date, str):
            last = sourced(date, html_url, commit_fetched)
        else:
            last = sourced(None, html_url, commit_fetched, "commit record has no committer date")
    claim_text = text
    claim_path = path
    if path and sha:
        status, pinned = read_skill_md(login, real_repo, sha, path)
        if status == 200 and frontmatter_name(pinned) == skill["slug"]:
            claim_text = pinned
    return (
        {"stars": stars, "skill_folder_last_commit": last, "login": login, "repo": real_repo, "branch": branch},
        branch,
        claim_path,
        claim_text,
    )


def author_and_folder(skill: dict, gh: dict, path: str | None, text: str | None) -> tuple[dict, dict]:
    login = gh.get("login") or skill["owner"]
    repo = gh.get("repo") or skill["repo"]
    branch = gh.get("branch") or "HEAD"
    sha_url = None
    commit_value = (gh.get("skill_folder_last_commit") or {}).get("value")
    commit_page = (gh.get("skill_folder_last_commit") or {}).get("url") or ""
    sha = commit_page.rstrip("/").split("/")[-1] if "/commit/" in commit_page else None
    fetched = now()
    if not path or not text:
        tried = raw_url(login, repo, branch, skill_md_candidates(skill)[0])
        claim = sourced(None, tried, fetched, "SKILL.md with this slug was not found in the public repo")
        folder_url = sourced(None, tried, fetched, "skill folder was not found because SKILL.md was not found")
        return claim, folder_url
    ref = sha or branch
    file_url = raw_url(login, repo, ref, path)
    # Re-stamp with the URL we can actually cite. The bytes were read during locate/pin.
    desc = parse_description(text)
    if desc:
        one_line = re.sub(r"\s+", " ", desc).strip()
        claim = sourced(f'"{one_line}"', file_url, fetched)
    else:
        claim = sourced(None, file_url, fetched, "SKILL.md has no description field in its frontmatter")
    folder = path.rsplit("/", 1)[0] if "/" in path else ""
    if folder:
        tree = f"https://github.com/{login}/{repo}/tree/{branch}/{folder}"
    else:
        tree = f"https://github.com/{login}/{repo}"
    folder_url = sourced(tree, file_url, fetched)
    return claim, folder_url


def parse_skillzbench(slug: str, owner: str, repo: str) -> list[dict]:
    url = f"https://skillzbench.com/skills/{slug}"
    fetched = now()
    status, html, final = HTTP.get(url)
    if status != 200:
        return missing("skillzbench", url, fetched, f"HTTP {status} from {url}")
    lines = html_lines(html)
    if "by" not in lines:
        if "1st-party" in lines:
            at = lines.index("1st-party")
            bits = []
            for line in lines[at : at + 4]:
                if line in {"·", "•"}:
                    break
                bits.append(line)
            reason = f"SkillzBench attributes slug {slug} to {' '.join(bits)}, which is not {owner}/{repo}"
        else:
            reason = f"SkillzBench page for slug {slug} has no owner/repo byline matching {owner}/{repo}"
        return missing("skillzbench", final, fetched, reason)
    idx = lines.index("by")
    parts = []
    for line in lines[idx + 1 : idx + 8]:
        if line in {"·", "•"}:
            break
        parts.append(line.strip().lstrip("/"))
    joined = "/".join(part for part in parts if part)
    page_owner, _, page_repo = joined.partition("/")
    if page_owner.lower() != owner.lower() or page_repo.lower() != repo.lower():
        return missing(
            "skillzbench",
            final,
            fetched,
            f"page byline is {page_owner}/{page_repo}, which does not match {owner}/{repo}",
        )
    rows = []
    headline_at = None
    for i, line in enumerate(lines):
        if line in {"Lift", "Quality"} and not (line == "Quality" and i + 1 < len(lines) and lines[i + 1].lower().startswith("judgment")):
            headline_at = i
            break
    if headline_at is None:
        rows.append(measurement(SOURCE_NAMES["skillzbench"], None, None, None, final, fetched, "no Lift or Quality headline on the page"))
    else:
        label = lines[headline_at]
        window = []
        for line in lines[headline_at + 1 : headline_at + 8]:
            if line in {"·", "•"}:
                continue
            window.append(line)
        model = window[0] if window else None
        rest = " ".join(window[1:]).replace("−", "-").replace("–", "-").replace("＋", "+")
        if "not yet benchmarked" in rest.lower():
            metric = "pass_rate_lift_pp" if label == "Lift" else "quality_lift_pts"
            rows.append(
                measurement(
                    SOURCE_NAMES["skillzbench"],
                    metric,
                    None,
                    model,
                    final,
                    fetched,
                    "SkillzBench page says this skill is not yet benchmarked",
                )
            )
        else:
            num = re.search(r"([+-]?\d+(?:\.\d+)?)\s+(pp|pts)", rest)
            if not num:
                rows.append(
                    measurement(
                        SOURCE_NAMES["skillzbench"],
                        label.lower(),
                        None,
                        model,
                        final,
                        fetched,
                        "headline was present but no pp or pts value was parsed",
                    )
                )
            else:
                unit = num.group(2)
                metric = "pass_rate_lift_pp" if unit == "pp" else "quality_lift_pts"
                value = f"{num.group(1)} {unit}"
                if "directional" in rest.lower():
                    value += " directional"
                rows.append(measurement(SOURCE_NAMES["skillzbench"], metric, value, model, final, fetched))
        trust_at = None
        for i in range(headline_at + 1, min(len(lines), headline_at + 12)):
            if lines[i] == "Trust":
                trust_at = i
                break
        if trust_at:
            for back in range(trust_at - 1, headline_at, -1):
                if re.fullmatch(r"\d{1,3}", lines[back]):
                    rows.append(
                        measurement(
                            SOURCE_NAMES["skillzbench"],
                            "trust_score",
                            int(lines[back]),
                            None,
                            final,
                            fetched,
                        )
                    )
                    break
    if "Quality judgment" in lines and "overall" in lines:
        overall_at = lines.index("overall", lines.index("Quality judgment"))
        if overall_at + 2 < len(lines) and lines[overall_at + 2] == "/10":
            rows.append(
                measurement(
                    SOURCE_NAMES["skillzbench"],
                    "quality_judgment_overall",
                    f"{lines[overall_at + 1]}/10",
                    None,
                    final,
                    fetched,
                )
            )
    return rows or missing("skillzbench", final, fetched, "no measurements parsed from the skill page")


DRIFT_VERDICTS = (
    "Too few answers to tell",
    "Clearly helped",
    "Clearly hurt",
    "No clear difference",
)


def drift_verdict(text: str) -> str | None:
    for phrase in DRIFT_VERDICTS:
        if phrase in text:
            return phrase
    return None


def drift_model(text: str, attr: str | None) -> str | None:
    named = re.search(r"\((claude-[a-z0-9._-]+)\)", text, re.I)
    if named:
        return named.group(1)
    if attr:
        return attr
    answering = re.search(r"Answering model:\s*([A-Za-z]+(?:\s+\d+(?:\.\d+)?)?)", text)
    return answering.group(1).strip() if answering else None


def parse_driftproof(html: str, fetched: str) -> tuple[dict[tuple[str, str, str], list[dict]], set[tuple[str, str]]]:
    found: dict[tuple[str, str, str], list[dict]] = {}
    bundles: set[tuple[str, str]] = set()
    index = "https://driftproofhq.com/skills/"

    def add(owner: str, repo: str, slug: str, row: dict) -> None:
        key = (owner.lower(), repo.lower(), slug.lower())
        bucket = found.setdefault(key, [])
        value = row.get("value") if isinstance(row.get("value"), dict) else {}
        signature = (value.get("with_skill"), value.get("without_skill"))
        for index, existing in enumerate(bucket):
            existing_value = existing.get("value") if isinstance(existing.get("value"), dict) else {}
            if (existing_value.get("with_skill"), existing_value.get("without_skill")) != signature:
                continue
            existing_model = existing.get("model") or ""
            new_model = row.get("model") or ""
            if existing_model == new_model:
                return
            # "Opus 5.5" and "claude-opus-5-5" are the same run. Keep the API id.
            if new_model.startswith("claude-") and not existing_model.startswith("claude-"):
                bucket[index] = row
                return
            if existing_model.startswith("claude-") and not new_model.startswith("claude-"):
                return
        bucket.append(row)

    score_re = re.compile(
        r"([0-9]+(?:\.[0-9]+)?)\s+with (?:the skill|it) and ([0-9]+(?:\.[0-9]+)?) without",
        re.I,
    )
    for entry in re.finditer(r'<li class="skill-entry"([^>]*)>([\s\S]*?)</li>', html):
        attrs = dict(re.findall(r'data-([a-z-]+)="([^"]*)"', entry.group(1)))
        page = (attrs.get("page") or "").strip("/")
        parts = page.split("/")
        if len(parts) < 3:
            continue
        owner, repo, slug = parts[0], parts[1], parts[2]
        text = strip_tags(entry.group(2))
        if "plugin bundle" in text.lower():
            bundles.add((owner.lower(), repo.lower()))
            continue
        if attrs.get("evidence") == "recomputed" and "not measured" in text.lower():
            continue
        scores = score_re.search(text)
        model = drift_model(text, None)
        hrefs = re.findall(r'href="(/r/[^"]+|/skills/[^"]+)"', entry.group(2))
        url = index
        for href in hrefs:
            if href.startswith("/r/"):
                url = "https://driftproofhq.com" + href
                break
        if scores:
            add(
                owner,
                repo,
                slug,
                measurement(
                    "Driftproof",
                    "with_vs_without_mean",
                    {
                        "with_skill": float(scores.group(1)),
                        "without_skill": float(scores.group(2)),
                        "verdict": drift_verdict(text),
                    },
                    model,
                    url,
                    fetched,
                ),
            )
    for row in re.finditer(r'<tr data-skill="([^"]+)">([\s\S]*?)</tr>', html):
        parts = row.group(1).split("/")
        if len(parts) < 3:
            continue
        owner, repo, slug = parts[0], parts[1], parts[2]
        for cell in re.finditer(r'<td([^>]*)>([\s\S]*?)</td>', row.group(2)):
            model_attr = re.search(r'data-model="([^"]+)"', cell.group(1))
            text = strip_tags(cell.group(2))
            scores = score_re.search(text)
            if not scores:
                continue
            record = re.search(r'href="(/r/[^"]+)"', cell.group(2))
            url = "https://driftproofhq.com" + record.group(1) if record else index
            model = drift_model(text, model_attr.group(1) if model_attr else None)
            add(
                owner,
                repo,
                slug,
                measurement(
                    "Driftproof",
                    "with_vs_without_mean",
                    {
                        "with_skill": float(scores.group(1)),
                        "without_skill": float(scores.group(2)),
                        "verdict": drift_verdict(text),
                    },
                    model,
                    url,
                    fetched,
                ),
            )
    return found, bundles


def load_driftproof() -> tuple[dict, set[tuple[str, str]], str, str, str]:
    url = "https://driftproofhq.com/skills/"
    fetched = now()
    status, html, final = HTTP.get(url, timeout=60)
    if status != 200:
        return {}, set(), final, fetched, f"HTTP {status} from {url}"
    found, bundles = parse_driftproof(html, fetched)
    return found, bundles, final, fetched, ""


def happycapy_rows(html: str, page_url: str, fetched: str) -> list[tuple[str, str, float, str | None]]:
    model = None
    marker = html.find("Model:")
    if marker >= 0:
        snippet = html[marker : marker + 600]
        named = re.search(r'font-medium">([^<]+)</span>', snippet)
        if named:
            model = named.group(1).strip()
    block_match = re.search(r"<h2[^>]*>\s*Leaderboard\s*</h2>([\s\S]*?)<h2", html)
    block = block_match.group(1) if block_match else ""
    rows = []
    pattern = re.compile(
        r'<span class="font-semibold text-foreground">([^<]+)</span>'
        r"[\s\S]*?<p class=\"mt-0\.5[^\"]*\">([\s\S]*?)</p>"
        r"[\s\S]*?<span class=\"w-9[^\"]*\">([^<]+)</span>"
    )
    for match in pattern.finditer(block):
        slug = match.group(1).strip()
        byline = strip_tags(match.group(2))
        owner_bit = byline.split("·")[0].strip().lower()
        try:
            score = float(match.group(3).strip())
        except ValueError:
            continue
        rows.append((slug, owner_bit, score, model))
    return rows


def load_happycapy() -> tuple[list[dict], str]:
    index = "https://happycapy.ai/skill-arena"
    fetched = now()
    status, html, final = HTTP.get(index)
    slugs = set(re.findall(r'href="(/skill-arena/[a-z0-9-]+)"', html or ""))
    wanted = []
    for path in sorted(slugs):
        name = path.rsplit("/", 1)[-1]
        if name.startswith("fig") or name.startswith("page-") or "icon" in name:
            continue
        wanted.append("https://happycapy.ai" + path)
    if status != 200:
        return [], f"HTTP {status} from {index}"
    records = []
    for url in wanted:
        page_fetched = now()
        page_status, page_html, page_final = HTTP.get(url)
        if page_status != 200:
            continue
        for slug, owner_bit, score, model in happycapy_rows(page_html, page_final, page_fetched):
            records.append(
                {
                    "slug": slug,
                    "owner_bit": owner_bit,
                    "score": score,
                    "model": model,
                    "url": page_final,
                    "fetched_at": page_fetched,
                }
            )
    return records, ""


def edge_catalog() -> tuple[list[dict], list[dict], str, str]:
    """Return (eval-data records, anthropic pptx task rows, index url, error)."""
    index = "https://getedge.cc/benchmarks/evaluations/"
    fetched = now()
    status, html, final = HTTP.get(index)
    if status != 200:
        return [], [], index, f"HTTP {status} from {index}"
    data_urls = sorted(set(re.findall(r'href="(/eval-data/[^"]+/index\.json)"', html)))
    records = []
    for path in data_urls:
        url = "https://getedge.cc" + path
        item_fetched = now()
        item_status, body, item_final = HTTP.get(url, headers={"Accept": "application/json"})
        if item_status != 200:
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("repo_url"):
            payload["_url"] = item_final
            payload["_fetched_at"] = item_fetched
            records.append(payload)
    pptx_rows = []
    group = re.search(r'<details class="skill-group" id="anthropics-pptx">([\s\S]*?)</details>', html)
    if group:
        for row in re.finditer(r"<tr[\s\S]*?</tr>", group.group(1)):
            cells_html = row.group(0)
            th = re.search(r"<th[^>]*>([\s\S]*?)</th>", cells_html)
            tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", cells_html)
            if not th or len(tds) < 2:
                continue
            task = strip_tags(re.sub(r"<small[\s\S]*?</small>", " ", th.group(1)))
            protocol_match = re.search(r"<small>([\s\S]*?)</small>", th.group(1))
            protocol = strip_tags(protocol_match.group(1)) if protocol_match else None
            try:
                without = float(strip_tags(tds[0]))
                with_skill = float(strip_tags(tds[1]))
            except ValueError:
                continue
            pptx_rows.append(
                measurement(
                    "Edge",
                    "mean_overall_judge_score",
                    {
                        "task": task,
                        "with_skill": with_skill,
                        "without_skill": without,
                        "protocol": protocol,
                        "scale": "score / 100",
                    },
                    None,
                    "https://getedge.cc/benchmarks/evaluations/#anthropics-pptx",
                    fetched,
                )
            )
    return records, pptx_rows, final, ""


def github_repo_from_url(url: str) -> tuple[str, str, str] | None:
    match = re.search(r"github\.com/([^/]+)/([^/]+)(?:/tree/[^/]+/?(.*))?$", url.strip())
    if not match:
        return None
    owner, repo, tail = match.group(1), match.group(2), match.group(3) or ""
    return owner, repo, tail.strip("/")


def edge_for_skill(skill: dict, owner: str, repo: str, folder: str, records: list[dict], pptx_rows: list[dict], error: str, index: str, fetched: str) -> list[dict]:
    if error:
        return missing("edge", index, fetched, error)
    rows = []
    for record in records:
        parsed = github_repo_from_url(record.get("repo_url") or "")
        if not parsed:
            continue
        rec_owner, rec_repo, tail = parsed
        if rec_owner.lower() != owner.lower() or rec_repo.lower() != repo.lower():
            continue
        tail_l = tail.lower()
        folder_l = (folder or "").lower()
        slug_l = skill["slug"].lower()
        path_ok = False
        if folder_l and folder_l in tail_l:
            path_ok = True
        elif not folder_l and (not tail_l or slug_l in tail_l or rec_repo.lower() == slug_l):
            path_ok = True
        elif slug_l and slug_l in tail_l:
            path_ok = True
        if not path_ok:
            continue
        model = record.get("model")
        for stat in record.get("stats") or []:
            if not isinstance(stat, dict) or "value" not in stat:
                continue
            rows.append(
                measurement(
                    "Edge",
                    stat.get("label") or "stat",
                    stat.get("value"),
                    model,
                    record["_url"],
                    record["_fetched_at"],
                )
            )
    if skill["slug"] == "pptx" and owner.lower() == "anthropics":
        rows.extend(pptx_rows)
    if rows:
        return rows
    return missing("edge", index, fetched, f"no Edge eval-data record matched {owner}/{repo} {folder or skill['slug']}")


def tessl_for_skill(owner: str, repo: str, slug: str, folder: str) -> list[dict]:
    names = [slug]
    leaf = folder.rstrip("/").split("/")[-1] if folder else ""
    if leaf and leaf not in names:
        names.append(leaf)
    tried = []
    for name in names:
        url = f"https://tessl.io/registry/skills/github/{owner}/{repo}/{name}"
        fetched = now()
        status, html, final = HTTP.get(url)
        tried.append(f"{url} -> HTTP {status}")
        if status != 200:
            continue
        if f"{owner}/{repo}".lower() not in html.lower() and f"{owner}/{repo}".lower() not in html_lines(html).__str__().lower():
            # The registry page for a different package can still 200. Require the repo path.
            if f"{owner}/{repo}" not in html:
                continue
        lines = html_lines(html)
        if f"{owner}/{repo}" not in " ".join(lines) and f"{owner}/{repo}" not in html:
            continue
        rows = []
        for i, line in enumerate(lines):
            if line == "Quality" and i + 1 < len(lines) and re.fullmatch(r"\d+(?:\.\d+)?%", lines[i + 1]):
                rows.append(measurement("Tessl", "quality", lines[i + 1], None, final, fetched))
                break
        for i, line in enumerate(lines):
            if line != "Impact" or i + 1 >= len(lines):
                continue
            nxt = lines[i + 1]
            if nxt in {"—", "-", "–"} or "no eval" in nxt.lower():
                rows.append(
                    measurement(
                        "Tessl",
                        "impact",
                        None,
                        None,
                        final,
                        fetched,
                        "Tessl page has no impact score (no eval scenarios)",
                    )
                )
            elif re.fullmatch(r"\d+(?:\.\d+)?%", nxt):
                value = nxt
                if i + 3 < len(lines) and re.fullmatch(r"\d+(?:\.\d+)?", lines[i + 2]) and lines[i + 3] == "x":
                    value = {"percent": nxt, "multiplier": lines[i + 2] + "x"}
                rows.append(measurement("Tessl", "impact", value, None, final, fetched))
            break
        if rows:
            return rows
        return missing("tessl", final, fetched, "registry page did not publish a Quality or Impact figure")
    url = f"https://tessl.io/registry/skills/github/{owner}/{repo}/{slug}"
    return missing("tessl", url, now(), "no public Tessl registry page; " + "; ".join(tried))


def load_openskilleval() -> tuple[dict | None, str, str, str]:
    url = "https://yingjiahao14.github.io/OpenSkillEval-Web/data/skills-detail.json"
    fetched = now()
    status, body, final = HTTP.get(url, headers={"Accept": "application/json"})
    if status != 200:
        return None, final, fetched, f"HTTP {status} from {url}"
    try:
        return json.loads(body), final, fetched, ""
    except json.JSONDecodeError:
        return None, final, fetched, "skills-detail.json was not valid JSON"


def description_overlap(author_claim: str | None, other: str) -> bool:
    """True when the two descriptions share a long normalized prefix."""
    if not author_claim or not other:
        return False

    def norm(value: str) -> str:
        value = value.strip().strip('"').lower()
        value = re.sub(r"[^a-z0-9 ]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    left, right = norm(author_claim), norm(other)
    shared = 0
    for a, b in zip(left, right):
        if a != b:
            break
        shared += 1
    return shared >= 28


def openskilleval_for_skill(skill: dict, claim: str | None, data: dict | None, url: str, fetched: str, error: str) -> list[dict]:
    if error or data is None:
        return missing("openskilleval", url, fetched, error or "OpenSkillEval data was not loaded")
    shorts = {skill["slug"], f"{skill['owner']}-{skill['slug']}"}
    if skill.get("ose_short"):
        shorts.add(skill["ose_short"])
    rows = []
    rejected_short = None
    for task, items in data.items():
        if not isinstance(items, list):
            continue
        for item in items:
            short = item.get("short")
            if short not in shorts:
                continue
            # Same short name is not enough: ppt-master and superdesign collide
            # with unrelated public entries. The author's description has to match.
            if not description_overlap(claim, item.get("description") or ""):
                rejected_short = short
                continue
            if item.get("avg_score") is None:
                continue
            rows.append(
                measurement(
                    "OpenSkillEval",
                    "avg_score",
                    {"avg_score": item.get("avg_score"), "n_results": item.get("n_results"), "task": task, "short": short},
                    None,
                    url,
                    fetched,
                )
            )
    if rows:
        return rows
    if rejected_short:
        reason = (
            f"skills-detail.json has short {rejected_short}, but its description does not match "
            "this skill's SKILL.md description, so the score was not used"
        )
    else:
        reason = f"no skills-detail.json entry matched {skill['slug']}"
    return missing("openskilleval", url, fetched, reason)


def load_swe() -> tuple[set[str], str, str, str]:
    paper = "https://arxiv.org/html/2603.15401v1"
    repo = "https://github.com/GeniusHTX/SWE-Skills-Bench"
    fetched = now()
    repo_status, _, _ = HTTP.get(repo)
    if repo_status == 404:
        note_open(
            "The SWE-Skills-Bench GitHub URL named in the paper "
            "(https://github.com/GeniusHTX/SWE-Skills-Bench) returned HTTP 404. "
            "Per-skill results were read from the public arXiv HTML table only."
        )
    status, html, final = HTTP.get(paper, timeout=60)
    if status != 200:
        return set(), paper, fetched, f"HTTP {status} from {paper}; GitHub repo HTTP {repo_status}"
    table = re.search(r'id="S4\.T2"([\s\S]{0,120000})', html)
    chunk = table.group(1) if table else html
    names = set()
    for row in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", chunk):
        cell = re.search(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", row.group(1))
        if not cell:
            continue
        name = strip_tags(cell.group(1))
        if name and name.lower() not in {"skills", "average"} and not name.startswith("\\"):
            names.add(name.strip())
    note = ""
    if repo_status != 200:
        note = f" GitHub repo HTTP {repo_status}."
    return names, final, fetched, note


def swe_for_skill(slug: str, names: set[str], url: str, fetched: str, error: str, note: str) -> list[dict]:
    if error and not names:
        return missing("swe_skills_bench", url, fetched, error)
    if slug in names:
        return [
            measurement(
                "SWE-Skills-Bench",
                "listed_in_table_2",
                True,
                None,
                url,
                fetched,
                "slug appears in Table 2 but this collector did not parse a numeric cell for it",
            )
        ]
    reason = (
        "not listed among the skill names in Table 2 of the public SWE-Skills-Bench paper"
        + (note or "")
    )
    return missing("swe_skills_bench", url, fetched, reason)


# Effect or outcome metrics. Only a non-null value whose metric is in this
# allowlist may set evidence_label. Every source has an explicit frozenset.
# There is no wildcard: a metric that is not listed does not count.
# SkillzBench pass-rate lift and quality lift are the headlines that count.
# Tessl quality, SkillzBench trust_score, and quality_judgment_overall are
# review or hygiene signals. They stay in the file and never set the label.
# Edge "recorded agent runs", "baseline outputs passed", and "skill outputs
# passed" are sample-size or arm counts, not a lift or a task score.
# SWE-Skills-Bench "listed_in_table_2" only records that a name appears in a
# table. The collector does not currently store a SWE effect metric.
EFFECT_METRICS = {
    "skillzbench": frozenset({"pass_rate_lift_pp", "quality_lift_pts"}),
    "tessl": frozenset({"impact"}),
    "driftproof": frozenset({"with_vs_without_mean"}),
    "happycapy": frozenset({"overall_score"}),
    "edge": frozenset({"mean_overall_judge_score", "wins / ties / losses"}),
    "openskilleval": frozenset({"avg_score"}),
    "swe_skills_bench": frozenset(),
}

# Metrics the collector knows about that must stay off the allowlist above.
EXCLUDED_METRICS = {
    "skillzbench": frozenset({"trust_score", "quality_judgment_overall"}),
    "tessl": frozenset({"quality"}),
    "edge": frozenset({
        "baseline outputs passed",
        "recorded agent runs",
        "skill outputs passed",
    }),
    "swe_skills_bench": frozenset({"listed_in_table_2"}),
}


def is_effect_measurement(source_key: str, row: dict) -> bool:
    if not isinstance(row, dict) or row.get("value") is None:
        return False
    allowed = EFFECT_METRICS.get(source_key)
    if not isinstance(allowed, frozenset):
        return False
    return row.get("metric") in allowed


def evidence_label(third_party: dict) -> str:
    for source_key, rows in third_party.items():
        for row in rows:
            if is_effect_measurement(source_key, row):
                return "measured_by_third_party"
    return "popular_but_unmeasured"


def probe_skills_sh_detail_api() -> None:
    url = "https://skills.sh/api/v1/skills/anthropics/skills/frontend-design"
    status, body, _ = HTTP.get(url, headers={"Accept": "application/json"})
    if status in {401, 403}:
        note_open(
            "skills.sh skill-detail API (GET /api/v1/skills/{id}) requires a Vercel OIDC token "
            f"(HTTP {status}). It was not called with any credential. Install counts come from "
            "the public skill page JSON-LD instead. The public audit API was used for Gen, Snyk, and Socket."
        )
    elif status != 200:
        note_open(f"skills.sh skill-detail API returned HTTP {status} without credentials; public pages were used for installs.")


def build() -> dict:
    seed = json.loads(SEED_PATH.read_text())
    print(f"seed skills: {len(seed)}", flush=True)
    probe_skills_sh_detail_api()
    print("loading Driftproof index", flush=True)
    drift_map, drift_bundles, drift_url, drift_fetched, drift_error = load_driftproof()
    print(f"  driftproof keys: {len(drift_map)}", flush=True)
    print("loading Happycapy arenas", flush=True)
    happy_rows, happy_error = load_happycapy()
    print(f"  happycapy rows: {len(happy_rows)}", flush=True)
    print("loading Edge eval-data", flush=True)
    edge_records, pptx_rows, edge_index, edge_error = edge_catalog()
    print(f"  edge records: {len(edge_records)} pptx rows: {len(pptx_rows)}", flush=True)
    print("loading OpenSkillEval", flush=True)
    ose_data, ose_url, ose_fetched, ose_error = load_openskilleval()
    print("loading SWE-Skills-Bench paper", flush=True)
    swe_names, swe_url, swe_fetched, swe_note = load_swe()
    swe_error = "" if swe_names else swe_note
    print(f"  swe names: {len(swe_names)}", flush=True)

    skills_out = []
    for skill in seed:
        print(f"collect {skill['owner']}/{skill['repo']}/{skill['slug']}", flush=True)
        sh = skills_sh(skill)
        owner = sh["page_owner"] or skill["owner"]
        repo = sh["page_repo"] or skill["repo"]
        gh, _branch, path, text = github_fields(skill, owner, repo)
        login = gh.get("login") or owner
        real_repo = gh.get("repo") or repo
        claim, folder_url = author_and_folder(skill, gh, path, text)
        folder = ""
        if path:
            folder = path.rsplit("/", 1)[0] if "/" in path else ""
        elif isinstance(skill.get("folder"), str):
            folder = skill["folder"]

        third = {
            "skillzbench": parse_skillzbench(skill["slug"], login, real_repo),
            "driftproof": drift_map.get((login.lower(), real_repo.lower(), skill["slug"].lower()))
            or (
                missing("driftproof", drift_url, drift_fetched, drift_error)
                if drift_error
                else missing(
                    "driftproof",
                    drift_url,
                    drift_fetched,
                    (
                        f"no per-skill Driftproof entry for {login}/{real_repo}/{skill['slug']}"
                        + (
                            " (a pack-level entry exists and was not copied onto this skill)"
                            if (login.lower(), real_repo.lower()) in drift_bundles
                            else ""
                        )
                    ),
                )
            ),
            "happycapy": [],
            "edge": edge_for_skill(skill, login, real_repo, folder, edge_records, pptx_rows, edge_error, edge_index, now()),
            "tessl": tessl_for_skill(login, real_repo, skill["slug"], folder),
            "openskilleval": openskilleval_for_skill(
                {**skill, "owner": login},
                claim.get("value"),
                ose_data,
                ose_url,
                ose_fetched,
                ose_error,
            ),
            "swe_skills_bench": swe_for_skill(skill["slug"], swe_names, swe_url, swe_fetched, swe_error, swe_note),
        }
        if happy_error:
            third["happycapy"] = missing("happycapy", "https://happycapy.ai/skill-arena", now(), happy_error)
        else:
            matched = []
            for row in happy_rows:
                if row["slug"] != skill["slug"]:
                    continue
                mapped = HAPPYCAPY_OWNERS.get(row["owner_bit"])
                if mapped != login.lower() and row["owner_bit"].replace(" ", "") != login.lower():
                    continue
                matched.append(
                    measurement(
                        "Happycapy",
                        "overall_score",
                        row["score"],
                        row["model"],
                        row["url"],
                        row["fetched_at"],
                    )
                )
            if matched:
                # One arena can repeat a skill; keep the first leaderboard hit per URL.
                deduped = []
                seen = set()
                for item in matched:
                    sig = (item["url"], item["value"], item["model"])
                    if sig in seen:
                        continue
                    seen.add(sig)
                    deduped.append(item)
                third["happycapy"] = deduped
            else:
                near = sorted({row["owner_bit"] for row in happy_rows if row["slug"] == skill["slug"]})
                if near:
                    happy_reason = (
                        f"slug {skill['slug']} is on a Happycapy leaderboard attributed to "
                        f"{', '.join(near)}, which does not match {login}"
                    )
                else:
                    happy_reason = f"no Happycapy skill-arena leaderboard row matched {login}/{skill['slug']}"
                third["happycapy"] = missing(
                    "happycapy",
                    "https://happycapy.ai/skill-arena",
                    now(),
                    happy_reason,
                )

        gh_public = {
            "stars": gh["stars"],
            "skill_folder_last_commit": gh["skill_folder_last_commit"],
        }
        skills_out.append(
            {
                "id": f"{login}/{real_repo}/{skill['slug']}",
                "job": skill["job"],
                "owner": login,
                "repo": real_repo,
                "slug": skill["slug"],
                "skill_folder_url": folder_url,
                "author_claim": claim,
                "skills_sh": {"installs": sh["installs"], "audits": sh["audits"]},
                "github": gh_public,
                "third_party": third,
                "evidence_label": evidence_label(third),
            }
        )
        installs = sh["installs"]["value"]
        stars = gh_public["stars"]["value"]
        print(f"  installs={installs} stars={stars} evidence={skills_out[-1]['evidence_label']}", flush=True)

    return {
        "schema_version": "1.0.0",
        "generated_at": now(),
        "open_questions": OPEN_QUESTIONS,
        "skills": skills_out,
    }


def main() -> None:
    document = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_PATH.relative_to(ROOT)} skills={len(document['skills'])}")
    print("open_questions:")
    if document["open_questions"]:
        for item in document["open_questions"]:
            print(f"- {item}")
    else:
        print("- none")


if __name__ == "__main__":
    main()
