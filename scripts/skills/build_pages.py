#!/usr/bin/env python3
"""Generate static /skills pages from data/skills/skills.json.

Reads the JSON file and writes site/skills/ plus sitemap entries.
Does not fetch, does not call a model, and does not invent run records.
A second run with the same inputs rewrites the same bytes.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from collect import (
    EXCLUDED_METRICS,
    SOURCE_NAMES,
    THIRD_PARTY_KEYS,
    is_effect_measurement,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "skills" / "skills.json"
RUNS_PATH = ROOT / "data" / "skills" / "runs.json"
SITE = ROOT / "site"
SITEMAP_PATH = SITE / "sitemap.xml"
ORIGIN = "https://luckysushi.ai"

JOBS = (
    ("frontend-design", "Frontend and design"),
    ("code-review-testing-debugging", "Code review, testing, and debugging"),
    ("docs-slides-writing", "Docs, slides, and writing"),
)
JOB_TITLES = dict(JOBS)

# Display labels are finer than the stored evidence_label. A stored
# "measured_by_third_party" value only means some effect metric was non-null.
# The page label says whether that result is firm, or the source itself
# called it directional or too small to tell. No scores are invented here.
DISPLAY_LABELS = (
    (
        "measured_by_us",
        "Measured by us",
        "We have run this skill on our tasks and stored the trials. No skill has this label yet.",
    ),
    (
        "third_party_result",
        "Third-party result",
        "Another project published a skill-level result, and it did not mark that result as directional or too small to tell.",
    ),
    (
        "too_early",
        "Too early to tell",
        "Every skill-level result is marked directional, or the source says there are too few answers to tell.",
    ),
    (
        "popular_but_unmeasured",
        "Popular but unmeasured",
        "Installs or stars are public, and no skill-level result is on file.",
    ),
)
DISPLAY_TEXT = {key: text for key, text, _blurb in DISPLAY_LABELS}
DISPLAY_BLURB = {key: blurb for key, _text, blurb in DISPLAY_LABELS}
SCORES_LINE = "Our own scores are coming; for now we show published evidence."
OSE_PAGE = "https://yingjiahao14.github.io/OpenSkillEval-Web/"
AUDIT_PATHS = {
    "gen": "agent-trust-hub",
    "snyk": "snyk",
    "socket": "socket",
}
WEAK_RE = re.compile(r"too few answers|directional", re.I)

METRIC_LABELS = {
    "pass_rate_lift_pp": "pass rate change",
    "quality_lift_pts": "quality change",
    "trust_score": "trust score",
    "quality_judgment_overall": "quality rating",
    "with_vs_without_mean": "with the skill and without it",
    "overall_score": "overall score",
    "mean_overall_judge_score": "judge score on a task",
    "wins / ties / losses": "wins, ties, and losses",
    "skill outputs passed": "skill outputs passed",
    "baseline outputs passed": "baseline outputs passed",
    "recorded agent runs": "recorded agent runs",
    "quality": "quality",
    "impact": "impact",
    "avg_score": "average score",
    "listed_in_table_2": "listed in a table",
}

AUDIT_TITLES = {
    "gen": "Gen audit",
    "snyk": "Snyk audit",
    "socket": "Socket audit",
}

RUN_FIELDS = (
    "run_id",
    "model",
    "harness_version",
    "skill_id",
    "skill_commit_sha",
    "task_id",
    "task_version",
    "seeds",
    "verifier_source",
    "token_cost",
    "rerun_command",
    "arms",
    "trials",
)
ARM_KEYS = ("no_skill", "skill", "length_matched_placebo")
ARM_TITLES = {
    "no_skill": "No skill",
    "skill": "Skill",
    "length_matched_placebo": "Length-matched placebo",
}

BANNED_RE = re.compile(r"\b(?:best|official|proof)\b", re.I)
VERBATIM_RE = re.compile(
    r"<(?P<tag>blockquote|span|p|div|pre)\b[^>]*\bclass=\"[^\"]*\bverbatim\b[^\"]*\"[^>]*>.*?</(?P=tag)>",
    re.S,
)
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
PRESERVED_LOCS = (
    "https://luckysushi.ai/",
    "https://luckysushi.ai/privacy",
)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def css_href() -> str:
    digest = hashlib.sha256((SITE / "styles.css").read_bytes()).hexdigest()[:10]
    return f"/styles.css?v={digest}"


def fmt_scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return json.dumps(value)
    if value is None:
        return "unavailable"
    return str(value)


def fmt_value(value) -> str:
    if isinstance(value, dict):
        return "; ".join(f"{key.replace('_', ' ')}: {fmt_value(inner)}" for key, inner in value.items())
    if isinstance(value, list):
        return ", ".join(fmt_value(item) for item in value)
    return fmt_scalar(value)


def measurement_fields(metric, value) -> dict:
    """Split a stored result into a figure, a with/without pair, and a note.

    Comparison results keep the two scores in their own fields. A single
    published figure stays with the row title. Notes are the source's own
    words, except the directional sentence, which is ours.
    """
    figure = None
    with_skill = None
    without_skill = None
    title = None
    source_notes: list[str] = []
    our_notes: list[str] = []
    if metric == "with_vs_without_mean" and isinstance(value, dict):
        title = "Mean score"
        with_skill = fmt_scalar(value.get("with_skill"))
        without_skill = fmt_scalar(value.get("without_skill"))
        if value.get("verdict"):
            source_notes.append(str(value.get("verdict")))
    elif metric == "mean_overall_judge_score" and isinstance(value, dict):
        title = str(value.get("task") or "Judge score on a task")
        with_skill = fmt_scalar(value.get("with_skill"))
        without_skill = fmt_scalar(value.get("without_skill"))
        if value.get("protocol"):
            source_notes.append(str(value.get("protocol")))
        if value.get("scale"):
            source_notes.append(f"Scale: {value.get('scale')}")
    elif metric == "impact" and isinstance(value, dict):
        bits = []
        if value.get("percent") is not None:
            bits.append(str(value.get("percent")))
        if value.get("multiplier"):
            bits.append(str(value.get("multiplier")))
        figure = ", ".join(bits) if bits else fmt_value(value)
    elif metric == "avg_score" and isinstance(value, dict):
        figure = fmt_scalar(value.get("avg_score"))
        extra = []
        if value.get("n_results") is not None:
            extra.append(f"{fmt_scalar(value.get('n_results'))} results")
        if value.get("task"):
            extra.append(f"task {value.get('task')}")
        if extra:
            source_notes.append(", ".join(extra))
    else:
        raw = fmt_value(value)
        if isinstance(value, str) and re.search(r"directional", value, re.I):
            figure = re.sub(r"\s*directional\b", "", value, flags=re.I).strip()
            our_notes.append("The source calls this directional.")
        else:
            figure = raw
    return {
        "title": title,
        "figure": figure,
        "with_skill": with_skill,
        "without_skill": without_skill,
        "source_notes": source_notes,
        "our_notes": our_notes,
    }


def fmt_measurement_value(metric, value) -> str:
    if metric == "with_vs_without_mean" and isinstance(value, dict):
        parts = [
            f"with skill {fmt_scalar(value.get('with_skill'))}",
            f"without skill {fmt_scalar(value.get('without_skill'))}",
        ]
        if value.get("verdict"):
            parts.append(f"The source says: {value.get('verdict')}")
        return "; ".join(parts)
    if metric == "mean_overall_judge_score" and isinstance(value, dict):
        parts = []
        if value.get("task"):
            parts.append(f"task: {value.get('task')}")
        parts.append(f"with skill {fmt_scalar(value.get('with_skill'))}")
        parts.append(f"without skill {fmt_scalar(value.get('without_skill'))}")
        if value.get("protocol"):
            parts.append(f"protocol: {value.get('protocol')}")
        if value.get("scale"):
            parts.append(f"scale: {value.get('scale')}")
        return "; ".join(parts)
    if metric == "impact" and isinstance(value, dict):
        parts = []
        if value.get("percent") is not None:
            parts.append(str(value.get("percent")))
        if value.get("multiplier"):
            parts.append(str(value.get("multiplier")))
        return ", ".join(parts) if parts else fmt_value(value)
    if metric == "avg_score" and isinstance(value, dict):
        parts = [f"average {fmt_scalar(value.get('avg_score'))}"]
        if value.get("n_results") is not None:
            parts.append(f"results {fmt_scalar(value.get('n_results'))}")
        if value.get("task"):
            parts.append(f"task {value.get('task')}")
        return "; ".join(parts)
    return fmt_value(value)


def host_label(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "source"


def ext_link(url: str, label: str | None = None) -> str:
    text = label or host_label(url)
    return f'<a href="{esc(url)}" rel="noopener">{esc(text)}</a>'


def fetched(row: dict) -> str:
    stamp = row.get("fetched_at") or ""
    shown = stamp.replace("T", " ").replace("Z", " UTC")
    return f'Fetched <time datetime="{esc(stamp)}">{esc(shown)}</time>'


def claim_text(value) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1].strip()
    return text


def show_time(stamp: str) -> str:
    return stamp.replace("T", " ").replace("Z", " UTC")


def effect_rows(skill: dict) -> list[tuple[str, dict]]:
    rows = []
    third = skill.get("third_party") or {}
    for source_key in THIRD_PARTY_KEYS:
        for row in third.get(source_key) or []:
            if is_effect_measurement(source_key, row):
                rows.append((source_key, row))
    return rows


def row_is_weak(row: dict) -> bool:
    value = row.get("value")
    if isinstance(value, dict):
        blob = " ".join(str(part) for part in value.values())
    elif value is None:
        blob = ""
    else:
        blob = str(value)
    return bool(WEAK_RE.search(blob))


def display_label_key(skill: dict) -> str:
    stored = skill.get("evidence_label")
    if stored == "measured_by_us":
        return "measured_by_us"
    effects = effect_rows(skill)
    if not effects:
        return "popular_but_unmeasured"
    if any(not row_is_weak(row) for _source_key, row in effects):
        return "third_party_result"
    return "too_early"


def label_text(skill: dict) -> str:
    key = display_label_key(skill)
    if key not in DISPLAY_TEXT:
        fail(f"{skill.get('id')} has an unknown display label {key}")
    return DISPLAY_TEXT[key]


def label_blurb(skill: dict) -> str:
    return DISPLAY_BLURB[display_label_key(skill)]


def counts_cell(source_key: str, row: dict) -> str:
    if not is_effect_measurement(source_key, row):
        return "No"
    if row_is_weak(row):
        return "Early only"
    return "Yes"


def source_link(source_key: str, url: str, skill: dict) -> str:
    href = readable_url(source_key, url, skill)
    label = "OpenSkillEval" if source_key == "openskilleval" else None
    return ext_link(href, label)


def readable_url(source_key: str, url: str, skill: dict) -> str:
    if source_key == "openskilleval" or (url and "skills-detail.json" in url):
        return OSE_PAGE
    if url and "api.github.com/repos/" in url:
        return f"https://github.com/{skill['owner']}/{skill['repo']}"
    return url


def audit_page_url(skill: dict, key: str) -> str:
    base = str(skill["skills_sh"]["installs"]["url"]).rstrip("/")
    return f"{base}/security/{AUDIT_PATHS[key]}"


def plain_reason(reason: str) -> str:
    text = (reason or "").strip()
    lowered = text.lower()
    if "pack-level" in lowered or "plugin bundle" in lowered:
        return "Only a pack-level result exists, and it is not copied onto this skill."
    if "description does not match" in lowered:
        return "A similar name is listed, but the description does not match this skill, so that score was not used."
    if (
        "does not match" in lowered
        or "attributed to" in lowered
        or "byline" in lowered
        or "attributes slug" in lowered
        or "which is not" in lowered
    ):
        return "A row exists under a different owner, so it was not used."
    if "not yet benchmarked" in lowered:
        return "This skill is not benchmarked there yet."
    if "not listed among" in lowered or "table 2" in lowered:
        return "Not listed in the paper table."
    if "http 404" in lowered:
        return "No public page for this skill."
    if "did not publish" in lowered:
        return "The registry page has no quality or impact figure."
    if lowered.startswith("no ") or " no " in lowered:
        return "No published row for this skill."
    return text


def fetched_phrase(stamps: list[str]) -> str:
    unique = []
    for stamp in stamps:
        if stamp and stamp not in unique:
            unique.append(stamp)
    if not unique:
        return ""
    if len(unique) == 1:
        stamp = unique[0]
        return f'Fetched <time datetime="{esc(stamp)}">{esc(show_time(stamp))}</time>'
    first, last = min(unique), max(unique)
    return (
        f'Fetched <time datetime="{esc(first)}">{esc(show_time(first))}</time>'
        f' to <time datetime="{esc(last)}">{esc(show_time(last))}</time>'
    )


def skill_path(skill: dict) -> str:
    return f"/skills/{skill['owner']}/{skill['slug']}/"


def skill_url(skill: dict) -> str:
    return ORIGIN + skill_path(skill)


def job_path(job: str) -> str:
    return f"/skills/jobs/{job}/"


def job_url(job: str) -> str:
    return ORIGIN + job_path(job)


def sorted_skills(skills: list[dict], job: str | None = None) -> list[dict]:
    chosen = [skill for skill in skills if job is None or skill["job"] == job]
    return sorted(chosen, key=lambda skill: (skill["slug"].casefold(), skill["owner"].casefold()))


def assert_identifier(value: str, label: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value or ""):
        fail(f"unsafe {label} {value!r}")


def pack_level_guard(skill: dict) -> None:
    for source_key, rows in (skill.get("third_party") or {}).items():
        for row in rows:
            reason = (row.get("reason") or "").lower()
            if row.get("value") is not None and ("pack-level" in reason or "plugin bundle" in reason):
                fail(f"{skill['id']} {source_key} carries a pack-level value")


def legend_html() -> str:
    rows = []
    for _key, name, blurb in DISPLAY_LABELS:
        rows.append(f"      <div><dt>{esc(name)}</dt><dd>{esc(blurb)}</dd></div>")
    return '    <dl class="legend">\n' + "\n".join(rows) + "\n    </dl>"


def skill_row(skill: dict) -> str:
    return (
        "<li>"
        f'<a href="{esc(skill_path(skill))}">{esc(skill["slug"])}</a>'
        f'<span class="note">{esc(skill["owner"])}</span>'
        f'<span class="tag">{esc(label_text(skill))}</span>'
        "</li>"
    )


def results_section(skill: dict) -> str:
    third = skill.get("third_party") or {}
    groups = []
    missing = []
    for source_key in THIRD_PARTY_KEYS:
        rows = list(third.get(source_key) or [])
        valued = [row for row in rows if row.get("value") is not None]
        empty = [row for row in rows if row.get("value") is None]
        if valued:
            groups.append((source_key, valued))
        missing.extend((source_key, row) for row in empty)
    stamps = [row.get("fetched_at") or "" for _source_key, rows in groups for row in rows]
    stamps.extend(row.get("fetched_at") or "" for _source_key, row in missing)
    when = fetched_phrase(stamps)
    parts = [
        "    <section>",
        "      <h2>Published results</h2>",
        "      <p>These are the figures other projects published for this skill. A pack-level result is not copied onto the skill.</p>",
    ]
    if when:
        parts.append(f'      <p class="note">{when}</p>')
    if groups:
        parts.append(
            '      <p class="note">Shown as published. Excluded from the evidence label. '
            "Counts toward the label is Yes when the row sets Third-party result, "
            "Early only when the source marked it directional or said there are too few answers to tell, "
            "and No when the figure is shown but does not count. "
            "A blank model means the source did not name one.</p>"
        )
        parts.append('      <table class="results">')
        parts.append(
            "        <thead><tr>"
            '<th scope="col">Result</th>'
            '<th scope="col">With the skill</th>'
            '<th scope="col">Without the skill</th>'
            '<th scope="col">Note</th>'
            '<th scope="col">Model</th>'
            '<th scope="col">Counts toward the label</th>'
            "</tr></thead>"
        )
        parts.append("        <tbody>")
        for source_key, rows in groups:
            source = rows[0].get("source") or SOURCE_NAMES.get(source_key, source_key)
            urls = []
            for row in rows:
                url = readable_url(source_key, row.get("url") or "", skill)
                if url and url not in urls:
                    urls.append(url)
            bits = [esc(source)]
            if len(urls) == 1:
                bits.append(source_link(source_key, rows[0].get("url") or "", skill))
            parts.append(f'          <tr class="group"><th colspan="6">{" · ".join(bits)}</th></tr>')
            for row in rows:
                metric = row.get("metric")
                fields = measurement_fields(metric, row.get("value"))
                metric_label = fields["title"] or METRIC_LABELS.get(metric, metric or "Result")
                name = esc(metric_label)
                if fields["figure"]:
                    name += f' <span class="verbatim">{esc(fields["figure"])}</span>'
                if len(urls) != 1:
                    name += " " + source_link(source_key, row.get("url") or "", skill)
                parts.append(
                    "          <tr>"
                    f'<th scope="row">{name}</th>'
                    f"{paired_cell(fields['with_skill'], 'With the skill')}"
                    f"{paired_cell(fields['without_skill'], 'Without the skill')}"
                    f"{note_cell(fields['source_notes'], fields['our_notes'])}"
                    f"{paired_cell(row.get('model'), 'Model')}"
                    f'<td data-label="Counts toward the label">{esc(counts_cell(source_key, row))}</td>'
                    "</tr>"
                )
        parts.append("        </tbody>")
        parts.append("      </table>")
    if missing:
        parts.append("      <h3>No skill-level result</h3>")
        parts.append('      <ul class="missing">')
        for source_key, row in missing:
            source = row.get("source") or SOURCE_NAMES.get(source_key, source_key)
            reason = plain_reason(row.get("reason") or "no reason recorded")
            parts.append(
                "        <li><strong>"
                f"{esc(source)}</strong>. {esc(reason)} "
                f"{source_link(source_key, row.get('url') or '', skill)}</li>"
            )
        parts.append("      </ul>")
    parts.append("    </section>")
    return "\n".join(parts)


def paired_cell(value, label: str) -> str:
    if value in (None, ""):
        return f'<td class="is-empty" data-label="{esc(label)}"></td>'
    return (
        f'<td data-label="{esc(label)}"><span class="verbatim">{esc(value)}</span></td>'
    )


def note_cell(source_notes: list[str], our_notes: list[str]) -> str:
    parts = []
    if source_notes:
        parts.append(f'<span class="verbatim">{esc(". ".join(source_notes))}</span>')
    parts.extend(esc(note) for note in our_notes)
    if not parts:
        return '<td class="is-empty" data-label="Note"></td>'
    return f'<td data-label="Note">{" ".join(parts)}</td>'


def header() -> str:
    return """  <header class="wrap top wide">
    <a class="brand" href="/">Lucky Sushi</a>
    <nav aria-label="Main"><a href="/skills/" aria-current="page">Skills</a><a href="https://luckysushi.substack.com/subscribe" rel="noopener">Subscribe</a></nav>
  </header>"""


def footer() -> str:
    return """  <footer class="wrap">
    <div class="foot">
      <p>&copy; 2026 Luckysushi LLC · Seattle, WA · <a href="https://luckysushi.substack.com" rel="noopener">Substack</a> · <a href="https://x.com/luckysushiai" rel="me noopener" target="_blank">X</a> · <a href="/privacy">Privacy</a></p>
    </div>
  </footer>"""


def section_nav(current: str) -> str:
    links = [
        ("/skills/", "All skills", "index"),
        ("/skills/jobs/frontend-design/", "Frontend and design", "frontend-design"),
        (
            "/skills/jobs/code-review-testing-debugging/",
            "Code review, testing, and debugging",
            "code-review-testing-debugging",
        ),
        ("/skills/jobs/docs-slides-writing/", "Docs, slides, and writing", "docs-slides-writing"),
        ("/skills/method/", "Method", "method"),
        ("/skills/runs/", "Run records", "runs"),
    ]
    parts = []
    for href, text, key in links:
        current_attr = ' aria-current="page"' if key == current else ""
        parts.append(f'<a href="{href}"{current_attr}>{esc(text)}</a>')
    return f'    <nav class="section-nav" aria-label="Skills">{"".join(parts)}</nav>'


def jsonld_script(data: dict) -> str:
    raw = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    raw = raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    indented = "\n".join("  " + line for line in raw.splitlines())
    return f'  <script type="application/ld+json">\n{indented}\n  </script>'


def web_page(title: str, description: str, canonical: str, main_entity: dict | None) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": canonical,
        "inLanguage": "en",
        "isPartOf": {
            "@type": "WebSite",
            "name": "Lucky Sushi",
            "url": ORIGIN + "/",
        },
    }
    if main_entity is not None:
        data["mainEntity"] = main_entity
    return data


def item_list(name: str, entries: list[tuple[str, str]]) -> dict:
    return {
        "@type": "ItemList",
        "name": name,
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "numberOfItems": len(entries),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": item_name,
                "url": url,
            }
            for index, (item_name, url) in enumerate(entries, start=1)
        ],
    }


def render_page(title: str, description: str, canonical: str, body: str, jsonld: dict) -> str:
    image = ORIGIN + "/assets/og-image.jpg"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta name="theme-color" content="#efe7de">
  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Lucky Sushi">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:image" content="{image}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="{image}">
  <link rel="stylesheet" href="{css_href()}">
{jsonld_script(jsonld)}
</head>
<body>
{header()}
<main>
  <div class="wrap sheet wide">
{body}
  </div>
</main>
{footer()}
</body>
</html>
"""


def unavailable_paragraph(row: dict) -> str:
    reason = row.get("reason") or "no reason recorded"
    return f'<p>Unavailable. <span class="verbatim">{esc(reason)}</span></p>'


def fact_block(title: str, row: dict, body_html: str, link_url: str | None = None) -> str:
    url = link_url or row["url"]
    return f"""    <section class="fact">
      <h3>{esc(title)}</h3>
{body_html}
      <p class="note">{ext_link(url)}</p>
    </section>"""


def audit_body(row: dict) -> str:
    value = row.get("value")
    if value is None:
        return unavailable_paragraph(row)
    if not isinstance(value, dict):
        return f'      <p class="verbatim">{esc(fmt_value(value))}</p>'
    parts = []
    if value.get("status"):
        parts.append(f'Status <span class="verbatim">{esc(value["status"])}</span>.')
    if value.get("risk_level"):
        parts.append(f'Risk <span class="verbatim">{esc(value["risk_level"])}</span>.')
    lines = []
    if parts:
        lines.append(f'      <p>{" ".join(parts)}</p>')
    elif not value.get("summary"):
        lines.append(f'      <p class="verbatim">{esc(fmt_value(value))}</p>')
    if value.get("summary"):
        lines.append(f'      <p class="verbatim">{esc(value["summary"])}</p>')
    return "\n".join(lines)


def number_body(row: dict) -> str:
    if row.get("value") is None:
        return unavailable_paragraph(row)
    return f"      <p>{esc(fmt_scalar(row['value']))}</p>"


def time_body(row: dict) -> str:
    if row.get("value") is None:
        return unavailable_paragraph(row)
    return f'      <p class="verbatim">{esc(show_time(str(row["value"])))}</p>'


def author_section(skill: dict) -> str:
    claim = skill["author_claim"]
    if claim.get("value") is None:
        quote = unavailable_paragraph(claim).strip()
    else:
        quote = f"<p>{esc(claim_text(claim.get('value')))}</p>"
    stamps = [claim.get("fetched_at") or ""]
    folder = skill.get("skill_folder_url") or {}
    if folder.get("fetched_at"):
        stamps.append(folder["fetched_at"])
    when = fetched_phrase(stamps)
    return f"""    <section>
      <h2>Author's claim</h2>
      <blockquote class="verbatim">
        {quote}
      </blockquote>
      <p class="note">Quoted from the description field of this skill's SKILL.md. {ext_link(claim["url"], "SKILL.md")}. {when}</p>
    </section>"""


def render_index(data: dict, skills: list[dict]) -> tuple[str, str, str]:
    canonical = ORIGIN + "/skills/"
    title = "Agent skills, and the evidence behind them · Lucky Sushi"
    description = (
        "A directory of twenty agent skills and the public evidence behind them. "
        "Inside each job the list is alphabetical by slug, with one evidence label per skill."
    )
    sections = []
    entries = []
    for job, job_title in JOBS:
        entries.append((job_title, job_url(job)))
        items = [skill_row(skill) for skill in sorted_skills(skills, job)]
        sections.append(
            f"""    <section>
      <h2 class="job"><a href="{esc(job_path(job))}">{esc(job_title)}</a></h2>
      <ul class="skill-index">
        {chr(10).join(items)}
      </ul>
    </section>"""
        )
    snapshot = show_time(data["generated_at"])
    body = f"""{section_nav("index")}
    <h1>Agent skills, and the evidence behind them</h1>
    <p>This directory lists agent skills for three kinds of work, and the public evidence behind each one. The label on each row says whether a project published a result, or the skill is only popular so far.</p>
    <p class="pending">{SCORES_LINE}</p>
    <p>Inside each job, skills are listed alphabetically by slug. This is not a ranking.</p>
    <h2 id="labels">What the labels mean</h2>
{legend_html()}
    <p class="note">Data snapshot {esc(snapshot)}. Collection notes are on the <a href="/skills/method/">method</a> page.</p>
{chr(10).join(sections)}
"""
    jsonld = web_page(title, description, canonical, item_list("Skills grouped by job", entries))
    return canonical, title, render_page(title, description, canonical, body, jsonld)


def render_jobs_index(data: dict, skills: list[dict]) -> tuple[str, str, str]:
    canonical = ORIGIN + "/skills/jobs/"
    title = "Skill jobs · Lucky Sushi"
    description = (
        "The three jobs in the skill directory: frontend and design, "
        "code review, testing, and debugging, and docs, slides, and writing."
    )
    items = []
    entries = []
    for job, job_title in JOBS:
        count = len(sorted_skills(skills, job))
        entries.append((job_title, job_url(job)))
        items.append(
            f'<li><a href="{esc(job_path(job))}">{esc(job_title)}</a> '
            f'<span class="note">{count} skills</span></li>'
        )
    body = f"""{section_nav("jobs")}
    <h1>Jobs</h1>
    <p class="pending">{SCORES_LINE}</p>
    <p>The <a href="/skills/">directory</a> groups skills into these three jobs. Each job page lists its skills alphabetically by slug.</p>
    <ul class="skill-index">
      {chr(10).join(items)}
    </ul>
    <p class="note">Data snapshot {esc(show_time(data["generated_at"]))}.</p>
"""
    jsonld = web_page(title, description, canonical, item_list("Skill jobs", entries))
    return canonical, title, render_page(title, description, canonical, body, jsonld)


def render_job(data: dict, skills: list[dict], job: str) -> tuple[str, str, str]:
    job_title = JOB_TITLES[job]
    canonical = job_url(job)
    title = f"{job_title} skills · Lucky Sushi"
    description = (
        f"{job_title} skills in the directory, listed alphabetically by slug. "
        "Each row has one evidence label."
    )
    entries = []
    items = []
    for skill in sorted_skills(skills, job):
        entries.append((f"{skill['owner']}/{skill['slug']}", skill_url(skill)))
        items.append(skill_row(skill))
    body = f"""{section_nav(job)}
    <p class="eyebrow"><a href="/skills/">Directory</a></p>
    <h1>{esc(job_title)}</h1>
    <p class="pending">{SCORES_LINE}</p>
    <p>These skills are listed alphabetically by slug. Each row shows one evidence label. The figures behind a label are on the skill page. <a href="/skills/#labels">What the labels mean</a>.</p>
    <p class="note">Data snapshot {esc(show_time(data["generated_at"]))}.</p>
    <ul class="skill-index">
      {chr(10).join(items)}
    </ul>
"""
    jsonld = web_page(
        title,
        description,
        canonical,
        item_list(f"{job_title} skills, alphabetical by slug", entries),
    )
    return canonical, title, render_page(title, description, canonical, body, jsonld)


def render_skill(data: dict, skill: dict) -> tuple[str, str, str]:
    canonical = skill_url(skill)
    title = f"{skill['slug']} by {skill['owner']} · Lucky Sushi"
    description = (
        f"{skill['owner']}/{skill['slug']}: {label_text(skill)}. "
        "Author's claim, published results, installs, audits, stars, and last commit, each with its source."
    )
    folder = skill["skill_folder_url"]
    if folder.get("value"):
        folder_line = f'Skill folder: {ext_link(folder["value"], "folder on GitHub")}.'
    else:
        reason = folder.get("reason") or "no reason recorded"
        folder_line = f'Folder unavailable. <span class="verbatim">{esc(reason)}</span>'
    repo_url = f"https://github.com/{skill['owner']}/{skill['repo']}"
    audits = skill["skills_sh"]["audits"]
    fact_rows = [
        ("Installs", skill["skills_sh"]["installs"], number_body(skill["skills_sh"]["installs"]), None),
        ("Gen audit", audits["gen"], audit_body(audits["gen"]), audit_page_url(skill, "gen")),
        ("Snyk audit", audits["snyk"], audit_body(audits["snyk"]), audit_page_url(skill, "snyk")),
        ("Socket audit", audits["socket"], audit_body(audits["socket"]), audit_page_url(skill, "socket")),
        ("GitHub stars", skill["github"]["stars"], number_body(skill["github"]["stars"]), repo_url),
        (
            "Last commit on the skill folder",
            skill["github"]["skill_folder_last_commit"],
            time_body(skill["github"]["skill_folder_last_commit"]),
            None,
        ),
    ]
    fact_html = "\n".join(
        fact_block(title, row, body, link) for title, row, body, link in fact_rows
    )
    fact_when = fetched_phrase([row.get("fetched_at") or "" for _title, row, _body, _link in fact_rows])
    body = f"""{section_nav("skill")}
    <p class="eyebrow"><a href="{esc(job_path(skill["job"]))}">{esc(JOB_TITLES[skill["job"]])}</a></p>
    <h1>{esc(skill["slug"])}</h1>
    <p class="tag">{esc(label_text(skill))}</p>
    <p>{esc(label_blurb(skill))} <a href="/skills/#labels">All labels</a>.</p>
    <p class="pending">{SCORES_LINE}</p>
    <p>{esc(skill["owner"])}/{esc(skill["repo"])}. {ext_link(repo_url, "Repository")}. {folder_line}</p>
{author_section(skill)}
{results_section(skill)}
    <section>
      <h2>Installs, audits, stars, and last commit</h2>
      <p>Each figure keeps the page it was read from. An unavailable value says so, with the reason.</p>
      <p class="note">{fact_when}</p>
{fact_html}
    </section>
    <p class="note">Data snapshot {esc(show_time(data["generated_at"]))}.</p>
"""
    folder_value = folder.get("value") or repo_url
    jsonld = web_page(
        title,
        description,
        canonical,
        {
            "@type": "SoftwareSourceCode",
            "name": skill["slug"],
            "codeRepository": folder_value,
            "programmingLanguage": "Markdown",
            "author": {"@type": "Organization", "name": skill["owner"]},
            "url": canonical,
        },
    )
    return canonical, title, render_page(title, description, canonical, body, jsonld)


def method_body(data: dict) -> str:
    edge_excluded = ", ".join(sorted(EXCLUDED_METRICS["edge"]))
    snapshot = show_time(data["generated_at"])
    return f"""{section_nav("method")}
    <h1>How skill evidence is collected</h1>
    <p class="pending">{SCORES_LINE}</p>
    <p>This page describes the public data behind the skill pages and the scoring plan. The words here are ours. Third-party sites are named so a figure can be traced, and their sentences are quoted on the skill pages rather than rewritten here.</p>
    <h2>What was collected</h2>
    <p>A collector in this repository reads public web pages and the GitHub REST API, then writes the JSON file the pages are generated from. It does not log into a site and it does not call a model API. Every stored value keeps the URL it came from and the UTC time of the fetch. When a value could not be read, the file stores a reason, and the skill page says what that means in plain language.</p>
    <p>The set is 20 skills in three jobs. The author's words on a skill page are the description field from that skill's SKILL.md, quoted above the published results.</p>
    <p>Install counts come from the public skills.sh page for that skill. The skills.sh detail API returned HTTP 401 when called without a credential, so the collector left it unused. Audit rows for Gen, Snyk, and Socket were read from the public skills.sh audit API. The skill page links to the readable audit page on skills.sh. GitHub stars are the star count of the repository, and the page links to that repository. The last commit is the newest commit that touched the skill folder, and the page links to that commit. OpenSkillEval scores were read from that project's published data. The skill page links to the OpenSkillEval site.</p>
    <p>The data snapshot for these pages is {esc(snapshot)}.</p>
    <h2>What each evidence label means</h2>
    <p>The <a href="/skills/">directory</a> shows one label on each row. The same four labels are explained under <a href="/skills/#labels">What the labels mean</a>.</p>
    <p><strong>Measured by us.</strong> We have run the skill on our tasks and stored the trials. No skill has this label yet.</p>
    <p><strong>Third-party result.</strong> Another project published a skill-level result, and it did not mark that result as directional or too small to tell. The results that can earn this label are a SkillzBench pass rate change, a SkillzBench quality change, Tessl impact, Driftproof with the skill and without it, a Happycapy overall score, an Edge judge score on a named task, Edge wins, ties, and losses, and an OpenSkillEval average score.</p>
    <p><strong>Too early to tell.</strong> The only skill-level results are ones the source marks as directional, or the source says there are too few answers to tell. Those rows stay on the skill page. They do not count as a third-party result.</p>
    <p><strong>Popular but unmeasured.</strong> Installs or stars are public, and no skill-level result is on file.</p>
    <p>Tessl quality, SkillzBench trust, and SkillzBench quality rating stay on the skill page when the source published them. They are shown as published, and excluded from the evidence label. The same exclusion covers Edge {esc(edge_excluded)}, and a SWE-Skills-Bench note that a name is listed in a table. A table listing is not a score. The SWE-Skills-Bench repository URL named in its paper returned HTTP 404, so the collector read the public paper table and stored no numeric SWE result.</p>
    <p>A result published for a pack, a plugin bundle, or a whole repository is not copied onto one skill inside it. When that is the only entry a source has, the skill page says the per-skill value is not available and gives the reason.</p>
    <h2>Three arms, once scoring starts</h2>
    <p>The planned comparison has three arms: no skill, the skill, and a length-matched placebo. The placebo is text of the same length as the skill, without the skill's instructions. Each arm is planned for repeated trials. A published score will include pass-rate lift, a confidence interval, tokens, and cost. Every score will name the model that produced it.</p>
    <p>The run record will name the model, the harness version, the skill commit, the task version, the seeds, the verifier, the pass or fail of each trial, the token cost, and the command that reruns it. Any cut to tasks or trials will be written into that record. Until a record exists, job pages stay in alphabetical order by slug.</p>
    <p>Run records will live under <a href="/skills/runs/">/skills/runs/</a>. None are recorded yet.</p>
"""


def render_method(data: dict) -> tuple[str, str, str]:
    canonical = ORIGIN + "/skills/method/"
    title = "How skill evidence is collected · Lucky Sushi"
    description = (
        "How skill pages collect public data, what each evidence label means, "
        "and the three planned arms: no skill, skill, and a length-matched placebo."
    )
    jsonld = web_page(
        title,
        description,
        canonical,
        {
            "@type": "CreativeWork",
            "headline": "How skill evidence is collected",
            "name": "How skill evidence is collected",
            "author": {"@type": "Organization", "name": "Lucky Sushi"},
        },
    )
    return canonical, title, render_page(title, description, canonical, method_body(data), jsonld)


def run_field_list() -> str:
    descriptions = {
        "run_id": "Stable id used in the page URL.",
        "model": "Model that produced the trials. A run page is not written without it.",
        "harness_version": "Harness name and version.",
        "skill_id": "Skill the run applied, as owner, repository, and slug.",
        "skill_commit_sha": "Skill commit that was loaded.",
        "task_id": "Task that was attempted.",
        "task_version": "Task version.",
        "seeds": "Seeds used for the trials.",
        "verifier_source": "Where the verifier comes from.",
        "token_cost": "Tokens and cost recorded for the run.",
        "rerun_command": "Command that repeats the run.",
        "arms": "The three arms: no skill, skill, and a length-matched placebo.",
        "trials": "Pass or fail for each trial, with its arm.",
    }
    return "\n".join(f"        <li><strong>{esc(key)}</strong>. {esc(descriptions[key])}</li>" for key in RUN_FIELDS)


def render_runs_index(runs: list[dict]) -> tuple[str, str, str]:
    canonical = ORIGIN + "/skills/runs/"
    title = "Skill run records · Lucky Sushi"
    if runs:
        description = f"{len(runs)} skill run records. Every record names its model."
        items = []
        entries = []
        for run in runs:
            run_id = str(run["run_id"])
            url = f"{ORIGIN}/skills/runs/{run_id}/"
            entries.append((run_id, url))
            items.append(
                f'<li><a href="/skills/runs/{esc(run_id)}/">{esc(run_id)}</a> '
                f'<span class="verbatim">{esc(run.get("model") or "")}</span></li>'
            )
        listing = "<ul>\n        " + "\n        ".join(items) + "\n      </ul>"
        lead = f"<p>{len(runs)} run records are on file. Each one names its model.</p>"
    else:
        description = (
            "No skill runs are recorded yet. A future run page will name its model, harness, "
            "task, seeds, trials, and rerun command."
        )
        entries = []
        listing = ""
        lead = "<p>No runs are recorded yet.</p>"
    body = f"""{section_nav("runs")}
    <h1>Run records</h1>
    <p class="pending">{SCORES_LINE}</p>
    {lead}
    <p>When a score is produced, its page will live at <code>/skills/runs/&lt;run-id&gt;/</code>. The generator writes that page only from a run record. It does not invent a run, a score, or a trial.</p>
    <h2>What a record contains</h2>
    <p>The template is ready for a later run. A record has to include every field below. The model is required, because every score names its model. The arms are no skill, the skill, and a length-matched placebo.</p>
    <ul>
{run_field_list()}
    </ul>
    {listing}
"""
    jsonld = web_page(title, description, canonical, item_list("Skill run records", entries))
    return canonical, title, render_page(title, description, canonical, body, jsonld)


def require_run(run: dict) -> None:
    missing = [key for key in RUN_FIELDS if key not in run or run[key] in (None, "")]
    if missing:
        fail("run record missing " + ", ".join(missing))
    if not str(run.get("model") or "").strip():
        fail(f"run {run.get('run_id')} is missing its model")
    arms = run["arms"]
    if not isinstance(arms, dict) or set(arms) != set(ARM_KEYS):
        fail(f"run {run.get('run_id')} arms must be no_skill, skill, and length_matched_placebo")
    trials = run["trials"]
    if not isinstance(trials, list) or not trials:
        fail(f"run {run.get('run_id')} needs at least one trial")
    for trial in trials:
        if not isinstance(trial, dict) or trial.get("arm") not in ARM_KEYS:
            fail(f"run {run.get('run_id')} has a trial outside the three arms")
        if not isinstance(trial.get("passed"), bool):
            fail(f"run {run.get('run_id')} trial passed must be a boolean")
    assert_identifier(str(run["run_id"]), "run_id")


def render_run_page(run: dict) -> tuple[str, str, str]:
    """Render one run record. Callers must pass a real record. This does not invent fields."""
    require_run(run)
    run_id = str(run["run_id"])
    canonical = f"{ORIGIN}/skills/runs/{run_id}/"
    title = f"Run {run_id} · Lucky Sushi"
    description = (
        f"Run record {run_id} for {run['skill_id']}. "
        f"Model: {run['model']}. Harness {run['harness_version']}."
    )
    arm_html = []
    for key in ARM_KEYS:
        arm_html.append(
            f"""    <section class="fact">
      <h3>{esc(ARM_TITLES[key])}</h3>
      <p class="verbatim">{esc(fmt_value(run["arms"][key]))}</p>
    </section>"""
        )
    trial_items = []
    for trial in run["trials"]:
        outcome = "pass" if trial["passed"] else "fail"
        index = trial.get("index", "")
        trial_items.append(
            f"<li>{esc(ARM_TITLES[trial['arm']])} trial {esc(index)}: {outcome}</li>"
        )
    optional = []
    for key, heading in (
        ("pass_rate_lift", "Pass-rate lift"),
        ("confidence_interval", "Confidence interval"),
        ("cuts", "Cuts recorded for this run"),
    ):
        if key in run and run[key] not in (None, "", [], {}):
            optional.append(
                f"""    <section class="fact">
      <h3>{esc(heading)}</h3>
      <p class="verbatim">{esc(fmt_value(run[key]))}</p>
    </section>"""
            )
    body = f"""{section_nav("runs")}
    <p class="eyebrow"><a href="/skills/runs/">Run records</a></p>
    <h1>Run {esc(run_id)}</h1>
    <p class="pending">Model: <span class="verbatim">{esc(run["model"])}</span></p>
    <p>This page is the stored record for one run. It names the model that produced the trials.</p>
    <section class="fact"><h3>Skill</h3><p class="verbatim">{esc(run["skill_id"])}</p><p>Commit <span class="verbatim">{esc(run["skill_commit_sha"])}</span></p></section>
    <section class="fact"><h3>Task</h3><p class="verbatim">{esc(run["task_id"])}</p><p>Version <span class="verbatim">{esc(run["task_version"])}</span></p></section>
    <section class="fact"><h3>Harness</h3><p class="verbatim">{esc(run["harness_version"])}</p></section>
    <section class="fact"><h3>Seeds</h3><p class="verbatim">{esc(fmt_value(run["seeds"]))}</p></section>
    <section class="fact"><h3>Verifier</h3><p>{ext_link(str(run["verifier_source"]))}</p></section>
    <section class="fact"><h3>Token cost</h3><p class="verbatim">{esc(fmt_value(run["token_cost"]))}</p></section>
    <h2>Arms</h2>
{chr(10).join(arm_html)}
    <h2>Trials</h2>
    <ul>
      {chr(10).join(trial_items)}
    </ul>
{chr(10).join(optional)}
    <h2>Rerun command</h2>
    <pre class="verbatim">{esc(run["rerun_command"])}</pre>
"""
    jsonld = web_page(
        title,
        description,
        canonical,
        {
            "@type": "CreativeWork",
            "name": f"Run record {run_id}",
            "author": {"@type": "Organization", "name": "Lucky Sushi"},
        },
    )
    return canonical, title, render_page(title, description, canonical, body, jsonld)


def load_runs() -> list[dict]:
    if not RUNS_PATH.exists():
        return []
    payload = json.loads(RUNS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        fail("data/skills/runs.json must be a list of run records")
    return payload


def check_label_rules() -> None:
    if is_effect_measurement("edge", {"value": "6", "metric": "recorded agent runs"}):
        fail("edge recorded agent runs must not count")
    if is_effect_measurement("edge", {"value": "0 of 3", "metric": "baseline outputs passed"}):
        fail("edge baseline outputs passed must not count")
    if is_effect_measurement("edge", {"value": "3 of 3", "metric": "skill outputs passed"}):
        fail("edge skill outputs passed must not count")
    if is_effect_measurement("swe_skills_bench", {"value": True, "metric": "listed_in_table_2"}):
        fail("listed_in_table_2 must not count")
    if is_effect_measurement("tessl", {"value": "70%", "metric": "quality"}):
        fail("tessl quality must not count")
    if is_effect_measurement("skillzbench", {"value": 78, "metric": "trust_score"}):
        fail("skillzbench trust_score must not count")
    if is_effect_measurement("skillzbench", {"value": "7.5/10", "metric": "quality_judgment_overall"}):
        fail("skillzbench quality judgment must not count")
    if not is_effect_measurement("edge", {"value": {"with_skill": 1}, "metric": "mean_overall_judge_score"}):
        fail("mean_overall_judge_score must count")
    if not is_effect_measurement("edge", {"value": "3 / 0 / 0", "metric": "wins / ties / losses"}):
        fail("edge wins / ties / losses must count")
    if not is_effect_measurement("tessl", {"value": {"percent": "97%"}, "metric": "impact"}):
        fail("tessl impact must count")


def our_copy_text(page_html: str) -> str:
    stripped = VERBATIM_RE.sub(" ", page_html)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    return stripped


def extract_jsonld(page_html: str) -> dict:
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        page_html,
        re.S,
    )
    if len(blocks) != 1:
        fail(f"expected one JSON-LD block, found {len(blocks)}")
    return json.loads(blocks[0])


def check_banned(page_html: str, where: str) -> None:
    text = our_copy_text(page_html)
    match = BANNED_RE.search(text)
    if match:
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 80)
        fail(f"banned word {match.group(0)!r} in {where}: {text[start:end]!r}")


RAW_LINK_RE = re.compile(r"skills-detail\.json|/api/v1/skills/audit/|api\.github\.com")


def check_public_copy(page_html: str, where: str) -> None:
    text = our_copy_text(page_html)
    if re.search(r"\bM[0-9]\b", text):
        fail(f"internal milestone name in {where}")
    if "—" in text or "–" in text:
        fail(f"em dash or en dash in {where}")
    if "Measured by a third party" in text:
        fail(f"old evidence label in {where}")
    if re.search(r"\bleaderboard\b", text, re.I):
        fail(f"leaderboard in our copy in {where}")
    if RAW_LINK_RE.search(page_html):
        fail(f"raw JSON source link in {where}")
    if page_html.count("Shown as published. Excluded from the evidence label.") > 1:
        fail(f"exclusion note repeats in {where}")
    for match in re.finditer(r"<li>(.*?)</li>", page_html, re.S):
        tags = re.findall(r'class="tag"', match.group(1))
        if len(tags) > 1:
            fail(f"evidence label appears {len(tags)} times in one row on {where}")


def check_display_labels(skills: list[dict]) -> None:
    by_id = {f"{skill['owner']}/{skill['slug']}": skill for skill in skills}
    expect = {
        "mattpocock/tdd": "too_early",
        "mattpocock/code-review": "too_early",
        "obra/test-driven-development": "too_early",
        "obra/requesting-code-review": "too_early",
        "addyosmani/code-review-and-quality": "too_early",
        "pbakaus/impeccable": "popular_but_unmeasured",
        "mattpocock/diagnosing-bugs": "popular_but_unmeasured",
        "obra/systematic-debugging": "popular_but_unmeasured",
        "hugohe3/ppt-master": "popular_but_unmeasured",
        "anthropics/frontend-design": "third_party_result",
        "anthropics/pptx": "third_party_result",
        "Leonxlnx/design-taste-frontend": "third_party_result",
    }
    for ident, key in expect.items():
        got = display_label_key(by_id[ident])
        if got != key:
            fail(f"{ident} display label is {got}, expected {key}")
    for skill in skills:
        key = display_label_key(skill)
        effects = effect_rows(skill)
        firm = [row for _source_key, row in effects if not row_is_weak(row)]
        weak = [row for _source_key, row in effects if row_is_weak(row)]
        if key == "popular_but_unmeasured" and effects:
            fail(f"{skill['id']} is popular but unmeasured and still has an effect row")
        if key == "too_early" and (firm or not weak):
            fail(f"{skill['id']} is too early with firm={bool(firm)} weak={bool(weak)}")
        if key == "third_party_result" and not firm:
            fail(f"{skill['id']} is a third-party result with no firm row")


def check_jsonld(page_html: str, canonical: str, main_type: str) -> str:
    data = extract_jsonld(page_html)
    if data.get("@context") != "https://schema.org":
        fail(f"{canonical} JSON-LD @context is {data.get('@context')!r}")
    if data.get("@type") != "WebPage":
        fail(f"{canonical} JSON-LD @type is {data.get('@type')!r}")
    if data.get("url") != canonical:
        fail(f"{canonical} JSON-LD url is {data.get('url')!r}")
    blob = json.dumps(data)
    if "aggregateRating" in blob or "ratingValue" in blob:
        fail(f"{canonical} JSON-LD includes a rating")
    main = data.get("mainEntity") or {}
    if main.get("@type") != main_type:
        fail(f"{canonical} mainEntity @type is {main.get('@type')!r}, expected {main_type}")
    return data["@type"] + "/" + main_type


def preserved_locs() -> list[str]:
    locs = []
    if SITEMAP_PATH.exists():
        text = SITEMAP_PATH.read_text(encoding="utf-8")
        for loc in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", text):
            if "/skills" in loc:
                continue
            if loc not in locs:
                locs.append(loc)
    for loc in PRESERVED_LOCS:
        if loc not in locs:
            locs.append(loc)
    return locs


def render_sitemap(locs: list[str]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="{SITEMAP_NS}">',
    ]
    for loc in locs:
        lines.append("  <url>")
        lines.append(f"    <loc>{esc(loc)}</loc>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def check_sitemap(sitemap: str, canonicals: list[str]) -> int:
    try:
        root = ET.fromstring(sitemap)
    except ET.ParseError as exc:
        fail(f"sitemap is not XML: {exc}")
    if root.tag != f"{{{SITEMAP_NS}}}urlset":
        fail(f"sitemap root is {root.tag}")
    locs = [el.text for el in root.findall(f"{{{SITEMAP_NS}}}url/{{{SITEMAP_NS}}}loc")]
    if any(not loc for loc in locs):
        fail("sitemap has an empty loc")
    if len(locs) != len(set(locs)):
        fail("sitemap has duplicate locs")
    for required in PRESERVED_LOCS:
        if required not in locs:
            fail(f"sitemap dropped {required}")
    for canonical in canonicals:
        if canonical not in locs:
            fail(f"sitemap missing {canonical}")
    extra = [loc for loc in locs if loc not in PRESERVED_LOCS and loc not in canonicals]
    if extra:
        fail(f"sitemap has unexpected locs {extra}")
    return len(locs)


def template_self_check() -> None:
    """Render a throwaway record in memory so the run template stays wired. Do not write it."""
    sample = {
        "run_id": "template-check",
        "model": "example-model",
        "harness_version": "benchflow example",
        "skill_id": "example/repo/slug",
        "skill_commit_sha": "abc123",
        "task_id": "task-1",
        "task_version": "1",
        "seeds": [1, 2, 3],
        "verifier_source": "https://example.com/verifier",
        "token_cost": {"tokens": 10, "cost": "0"},
        "rerun_command": "python3 -m benchflow rerun template-check",
        "arms": {
            "no_skill": "instruction only",
            "skill": "instruction plus the skill",
            "length_matched_placebo": "instruction plus length-matched filler",
        },
        "trials": [
            {"arm": "no_skill", "index": 1, "passed": False},
            {"arm": "skill", "index": 1, "passed": True},
            {"arm": "length_matched_placebo", "index": 1, "passed": False},
        ],
    }
    canonical, _title, page_html = render_run_page(sample)
    check_banned(page_html, "run template")
    check_jsonld(page_html, canonical, "CreativeWork")
    if "example-model" not in page_html:
        fail("run template dropped the model")


def build() -> tuple[list[tuple[Path, str, str, str]], str]:
    check_label_rules()
    template_self_check()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    skills = data["skills"]
    if len(skills) != 20:
        fail(f"expected 20 skills, found {len(skills)}")
    for skill in skills:
        assert_identifier(skill["owner"], "owner")
        assert_identifier(skill["slug"], "slug")
        if skill["job"] not in JOB_TITLES:
            fail(f"unknown job {skill['job']}")
        pack_level_guard(skill)
    check_display_labels(skills)
    runs = load_runs()
    for run in runs:
        require_run(run)

    pages: list[tuple[Path, str, str, str]] = []

    def add(relpath: str, canonical: str, page_html: str, main_type: str) -> None:
        pages.append((SITE / relpath, page_html, canonical, main_type))

    canonical, _title, page_html = render_index(data, skills)
    add("skills/index.html", canonical, page_html, "ItemList")
    canonical, _title, page_html = render_jobs_index(data, skills)
    add("skills/jobs/index.html", canonical, page_html, "ItemList")
    for job, _title in JOBS:
        canonical, _title, page_html = render_job(data, skills, job)
        add(f"skills/jobs/{job}/index.html", canonical, page_html, "ItemList")
    for skill in sorted_skills(skills):
        canonical, _title, page_html = render_skill(data, skill)
        add(f"skills/{skill['owner']}/{skill['slug']}/index.html", canonical, page_html, "SoftwareSourceCode")
    canonical, _title, page_html = render_runs_index(runs)
    add("skills/runs/index.html", canonical, page_html, "ItemList")
    for run in sorted(runs, key=lambda item: str(item["run_id"])):
        canonical, _title, page_html = render_run_page(run)
        add(f"skills/runs/{run['run_id']}/index.html", canonical, page_html, "CreativeWork")
    canonical, _title, page_html = render_method(data)
    add("skills/method/index.html", canonical, page_html, "CreativeWork")

    titles = []
    descriptions = []
    canonicals = []
    for path, page_html, canonical, main_type in pages:
        where = str(path.relative_to(ROOT))
        check_banned(page_html, where)
        check_public_copy(page_html, where)
        kind = check_jsonld(page_html, canonical, main_type)
        print(f"jsonld ok {canonical} {kind}")
        title = re.search(r"<title>(.*?)</title>", page_html).group(1)
        description = re.search(r'<meta name="description" content="(.*?)">', page_html).group(1)
        if title in titles:
            fail(f"duplicate title {title}")
        if description in descriptions:
            fail(f"duplicate description {description}")
        if len(description) < 40:
            fail(f"short description for {canonical}")
        titles.append(title)
        descriptions.append(description)
        canonicals.append(canonical)
        if 'rel="canonical"' not in page_html:
            fail(f"{canonical} missing canonical link")

    locs = preserved_locs() + canonicals
    sitemap = render_sitemap(locs)
    count = check_sitemap(sitemap, canonicals)
    rels = [path.relative_to(SITE).as_posix() for path, *_rest in pages]
    n_jobs = sum(
        1
        for rel in rels
        if rel.startswith("skills/jobs/") and rel.endswith("/index.html") and rel.count("/") == 3
    )
    n_skills = sum(
        1
        for rel in rels
        if rel.startswith("skills/")
        and rel.endswith("/index.html")
        and rel.count("/") == 3
        and not rel.startswith("skills/jobs/")
        and not rel.startswith("skills/runs/")
    )
    n_run_pages = sum(1 for rel in rels if rel.startswith("skills/runs/") and rel.count("/") == 3)
    print(
        "page_count "
        f"index=1 jobs_index=1 jobs={n_jobs} skills={n_skills} runs_index=1 method=1 "
        f"run_records={n_run_pages} total={len(pages)}"
    )
    print(f"sitemap ok urls={count}")
    print("banned_words ok")
    if "skills/jobs/index.html" not in rels:
        fail("missing skills/jobs/index.html")
    if n_jobs != 3 or n_skills != 20 or len(pages) != 27 + n_run_pages:
        fail(f"unexpected page count total={len(pages)} skills={n_skills} jobs={n_jobs}")
    tdd_html = next(html for path, html, _canonical, _main in pages if path.name == "index.html" and path.parent.name == "tdd")
    if "Too early to tell" not in tdd_html:
        fail("tdd page lost the too-early label")
    if tdd_html.count("Shown as published. Excluded from the evidence label.") != 1:
        fail("tdd page should state the exclusion note once")
    if len(re.findall(r"Fetched <time", tdd_html)) != 3:
        fail("tdd page should state Fetched once per section")
    if "without skill" in tdd_html or "; The source says:" in tdd_html:
        fail("tdd comparison result is still a run-on string")
    pptx_html = next(
        html for path, html, _canonical, _main in pages if path.parent.name == "pptx" and path.name == "index.html"
    )
    if "without skill" in pptx_html or "task: Build a board" in pptx_html:
        fail("pptx comparison result is still a run-on string")
    if "Counts toward the label" not in tdd_html or "Early only" not in tdd_html:
        fail("tdd page is missing the plain counts column")
    if 'href="/#bench"' in tdd_html or ">Rally<" in tdd_html:
        fail("skills header still links Rally at a homepage anchor")
    if "/security/snyk" not in tdd_html or "/security/agent-trust-hub" not in tdd_html:
        fail("tdd audits do not link to the readable skills.sh pages")
    return pages, sitemap


def write_outputs(pages: list[tuple[Path, str, str, str]], sitemap: str) -> None:
    expected = set()
    for path, page_html, _canonical, _main in pages:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_html, encoding="utf-8")
        expected.add(path.resolve())
    skills_root = SITE / "skills"
    for path in sorted(skills_root.rglob("*"), reverse=True):
        if path.is_file() and path.resolve() not in expected:
            path.unlink()
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    SITEMAP_PATH.write_text(sitemap, encoding="utf-8")


def main() -> None:
    pages, sitemap = build()
    write_outputs(pages, sitemap)
    print(f"wrote {len(pages)} pages and site/sitemap.xml")


if __name__ == "__main__":
    main()
