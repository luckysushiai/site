#!/usr/bin/env python3
"""Stamp /styles.css links in site/*.html with ?v=<sha256[:10]> of styles.css.

Browsers cache styles.css for 1 hour (site/_headers), so an unversioned URL can show the
new HTML with the old CSS after a deploy. Run this after any styles.css change, then commit.
"""
import glob, hashlib, re
v = hashlib.sha256(open("site/styles.css", "rb").read()).hexdigest()[:10]
for p in glob.glob("site/*.html"):
    s = open(p).read()
    n = re.sub(r'href="/styles\.css(\?v=[0-9a-f]+)?"', f'href="/styles.css?v={v}"', s)
    if n != s:
        open(p, "w").write(n)
    print(p, "->", f"/styles.css?v={v}")
