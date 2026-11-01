import re

_CORE = re.compile(r"^(0|[1-9]\d*)$")
_IDENT = re.compile(r"^[0-9A-Za-z-]+$")


def _sign(left, right):
    return (left > right) - (left < right)


def _parse(raw):
    if not isinstance(raw, str) or raw == "" or "+" in raw:
        raise ValueError("invalid semver")
    if "-" in raw:
        core_raw, pre_raw = raw.split("-", 1)
        if pre_raw == "":
            raise ValueError("invalid semver")
    else:
        core_raw, pre_raw = raw, None
    parts = core_raw.split(".")
    if len(parts) != 3 or any(_CORE.fullmatch(part) is None for part in parts):
        raise ValueError("invalid semver")
    core = tuple(int(part) for part in parts)
    if pre_raw is None:
        return core, None
    parsed = []
    for ident in pre_raw.split("."):
        if ident == "" or _IDENT.fullmatch(ident) is None:
            raise ValueError("invalid semver")
        if ident.isdigit():
            if _CORE.fullmatch(ident) is None:
                raise ValueError("invalid semver")
            parsed.append(("num", int(ident)))
        else:
            parsed.append(("str", ident))
    return core, tuple(parsed)


def _cmp_id(left, right):
    if left[0] == "num" and right[0] == "num":
        return _sign(left[1], right[1])
    if left[0] == "num":
        return -1
    if right[0] == "num":
        return 1
    return _sign(left[1], right[1])


def _cmp_pre(left, right):
    limit = min(len(left), len(right))
    for index in range(limit):
        compared = _cmp_id(left[index], right[index])
        if compared != 0:
            return compared
    return _sign(len(left), len(right))


def cmp_semver(left, right):
    left_core, left_pre = _parse(left)
    right_core, right_pre = _parse(right)
    for left_part, right_part in zip(left_core, right_core):
        compared = _sign(left_part, right_part)
        if compared != 0:
            return compared
    if left_pre is None and right_pre is None:
        return 0
    if left_pre is None:
        return 1
    if right_pre is None:
        return -1
    return _cmp_pre(left_pre, right_pre)
