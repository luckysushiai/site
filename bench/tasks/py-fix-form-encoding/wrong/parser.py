def _plus(raw):
    return raw.replace("+", " ")


def parse_qs(raw):
    if raw == "":
        return {}
    out = {}
    for part in raw.split("&"):
        if part == "":
            continue
        if "=" not in part:
            key, value = part, ""
        else:
            key, value = part.split("=", 1)
        out[_plus(key)] = _plus(value)
    return out
