def parse_qs(raw):
    if raw == "":
        return {}
    out = {}
    for part in raw.split("&"):
        if part == "":
            continue
        if "=" not in part:
            out[part] = ""
            continue
        key, value = part.split("=", 1)
        out[key] = value
    return out
