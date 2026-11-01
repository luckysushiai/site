import access


def test_missing_user():
    assert access.access_decision(None, {"public": True}) == "deny"


def test_public_resource():
    user = {"id": 1, "role": "viewer", "disabled": False}
    assert access.access_decision(user, {"public": True, "owner": 9}) == "allow"
