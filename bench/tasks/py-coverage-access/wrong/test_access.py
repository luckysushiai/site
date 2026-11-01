import access


def test_missing_user():
    assert access.access_decision(None, {"public": True}) == "deny"


def test_public_resource():
    user = {"id": 1, "role": "viewer", "disabled": False}
    assert access.access_decision(user, {"public": True, "owner": 9}) == "allow"


def test_admin():
    user = {"id": 1, "role": "admin", "disabled": False}
    resource = {"public": False, "owner": 9, "shared_with": [], "viewers": []}
    assert access.access_decision(user, resource) == "allow"
