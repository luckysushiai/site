import access


def test_missing_user():
    assert access.access_decision(None, {"public": True}) == "deny"


def test_missing_resource():
    assert access.access_decision({"id": 1}, None) == "deny"


def test_disabled():
    user = {"id": 1, "role": "admin", "disabled": True}
    assert access.access_decision(user, {"public": True}) == "deny"


def test_public_resource():
    user = {"id": 1, "role": "viewer", "disabled": False}
    assert access.access_decision(user, {"public": True, "owner": 9}) == "allow"


def test_admin():
    user = {"id": 1, "role": "admin", "disabled": False}
    resource = {"public": False, "owner": 9, "shared_with": [], "viewers": []}
    assert access.access_decision(user, resource) == "allow"


def test_editor_owner():
    user = {"id": 4, "role": "editor", "disabled": False}
    resource = {"public": False, "owner": 4, "shared_with": [], "viewers": []}
    assert access.access_decision(user, resource) == "allow"


def test_editor_shared():
    user = {"id": 4, "role": "editor", "disabled": False}
    resource = {"public": False, "owner": 8, "shared_with": ["editor"], "viewers": []}
    assert access.access_decision(user, resource) == "allow"


def test_viewer_list():
    user = {"id": 5, "role": "viewer", "disabled": False}
    resource = {"public": False, "owner": 8, "shared_with": [], "viewers": [5]}
    assert access.access_decision(user, resource) == "view"


def test_stranger():
    user = {"id": 5, "role": "viewer", "disabled": False}
    resource = {"public": False, "owner": 8, "shared_with": [], "viewers": [9]}
    assert access.access_decision(user, resource) == "deny"


def test_editor_without_a_share():
    user = {"id": 4, "role": "editor", "disabled": False}
    resource = {"public": False, "owner": 8, "shared_with": [], "viewers": []}
    assert access.access_decision(user, resource) == "deny"
