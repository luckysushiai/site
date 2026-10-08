#!/usr/bin/env python3
"""Build a Cloudflare Pages Direct Upload payload from ./site (run from repo root).

Writes to /tmp/lsdeploy/: upload.json (POST /pages/assets/upload body), hashes.json
(check-missing / upsert-hashes body), manifest.json (the deployment "manifest" form field).
Skips _headers (sent as its own form field) and unreferenced assets/icon-source.png.
Hash = sha256(base64 + ext)[:32]; Pages treats the key as an opaque 32-hex id.
"""
import base64, hashlib, json, os
SKIP = {"/_headers", "/assets/icon-source.png"}
CT = {".html": "text/html", ".css": "text/css", ".txt": "text/plain", ".xml": "application/xml",
      ".webmanifest": "application/manifest+json", ".ico": "image/x-icon", ".png": "image/png",
      ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp", ".js": "text/javascript"}
os.makedirs("/tmp/lsdeploy", exist_ok=True)
manifest, payload = {}, []
for dp, _, fns in os.walk("site"):
    for f in sorted(fns):
        p = os.path.join(dp, f)[len("site"):]
        if p in SKIP:
            continue
        b64 = base64.b64encode(open("site" + p, "rb").read()).decode()
        ext = os.path.splitext(f)[1]
        h = hashlib.sha256((b64 + ext[1:]).encode()).hexdigest()[:32]
        manifest[p] = h
        payload.append({"key": h, "value": b64, "metadata": {"contentType": CT.get(ext, "application/octet-stream")}, "base64": True})
json.dump(payload, open("/tmp/lsdeploy/upload.json", "w"))
json.dump({"hashes": [x["key"] for x in payload]}, open("/tmp/lsdeploy/hashes.json", "w"))
json.dump(manifest, open("/tmp/lsdeploy/manifest.json", "w"), separators=(",", ":"))
print(json.dumps(manifest, separators=(",", ":")))
