def access_decision(user, resource):
    if user is None or resource is None:
        return "deny"
    if user.get("disabled"):
        return "deny"
    if resource.get("public"):
        return "allow"
    role = user.get("role")
    if role == "admin":
        return "allow"
    if role == "editor" and resource.get("owner") == user.get("id"):
        return "allow"
    if role == "editor" and "editor" in resource.get("shared_with", []):
        return "allow"
    if user.get("id") in resource.get("viewers", []):
        return "view"
    return "deny"
