#!/usr/bin/env python3
"""Stamp /styles.css links in site HTML with ?v=<sha256[:10]> of styles.css.

Browsers cache styles.css for 1 hour (site/_headers), so an unversioned URL can show the
new HTML with the old CSS after a deploy. Run this after any styles.css change, then commit.
"""
import hashlib
import re
from pathlib import Path

root = Path("site")
digest = hashlib.sha256((root / "styles.css").read_bytes()).hexdigest()[:10]
href = f"/styles.css?v={digest}"
for path in sorted(root.rglob("*.html")):
    text = path.read_text(encoding="utf-8")
    updated = re.sub(r'href="/styles\.css(\?v=[0-9a-f]+)?"', f'href="{href}"', text)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
    print(path, "->", href)
