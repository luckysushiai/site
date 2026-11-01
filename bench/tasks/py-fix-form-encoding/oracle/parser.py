def _decode(raw):
    chars = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == "+":
            chars.append(" ")
            index += 1
        elif char == "%" and index + 2 < len(raw):
            chars.append(chr(int(raw[index + 1:index + 3], 16)))
            index += 3
        else:
            chars.append(char)
            index += 1
    return "".join(chars)


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
        out[_decode(key)] = _decode(value)
    return out
