from datetime import datetime
from typing import Tuple

from cidc_api.models import Users, UserSchema, CIDCRole

from ..utils import mock_current_user, make_admin


def setup_users(cidc_api, monkeypatch, registered=True) -> Tuple[int, int]:
    """
    Insert two users into the database. If `registered=False`, don't
    register the first user.
    """
    current_user = Users(id=1, email="test@email.com")
    other_user = Users(id=2, email="other@email.org")

    mock_current_user(current_user, monkeypatch)

    with cidc_api.app_context():
        if registered:
            current_user.role = CIDCRole.CIMAC_USER.value
            current_user.approval_date = datetime.now()
        current_user.insert()
        other_user.insert()

        return current_user.id, other_user.id


def register_user(user_id, app):
    """Register the given user as a cimac-user."""
    with app.app_context():
        user = Users.find_by_id(user_id)
        user.approval_date = datetime.now()
        user.role = CIDCRole.CIMAC_USER.value
        user.update()


def test_get_self(cidc_api, clean_db, monkeypatch):
    """Check that get self returns the current user's info."""
    user_id, _ = setup_users(cidc_api, monkeypatch, registered=False)

    with cidc_api.app_context():
        user = Users.find_by_id(user_id)

    client = cidc_api.test_client()

    res = client.get("users/self")
    assert res.status_code == 200
    assert res.json == UserSchema().dump(user)


def test_create_self(cidc_api, clean_db, monkeypatch):
    """Check that a user can create themself."""
    new_user_json = {"email": "test@email.com"}
    new_user = Users(**new_user_json)

    mock_current_user(new_user, monkeypatch)

    client = cidc_api.test_client()

    # A user can't create a user record with a different email than their own
    res = client.post("/users/self", json={"email": "some.other@email.com"})
    assert res.status_code == 400
    assert "can't create a user with email" in res.json["message"]

    # A user can create themselves
    res = client.post("/users/self", json=new_user_json)
    assert res.status_code == 201
    assert "id" in res.json
    assert res.json["email"] == new_user.email


def test_list_users(cidc_api, clean_db, monkeypatch):
    """Check that listing users works as expected."""
    user_id, other_user_id = setup_users(cidc_api, monkeypatch, registered=True)

    client = cidc_api.test_client()

    # Registered users who aren't admins can't list users
    register_user(user_id, cidc_api)
    res = client.get("/users")
    assert res.status_code == 401
    assert "not authorized" in res.json["message"]

    # Admins can list users
    make_admin(user_id, cidc_api)
    res = client.get("/users")
    assert res.status_code == 200
    assert len(res.json) == 2
    assert set([u["id"] for u in res.json]) == set([user_id, other_user_id])


def test_get_user(cidc_api, clean_db, monkeypatch):
    """Check that getting users by ID works as expected."""
    user_id, other_user_id = setup_users(cidc_api, monkeypatch, registered=True)

    client = cidc_api.test_client()

    # Non-admins can't get themselves or other users by their IDs
    assert client.get(f"/users/{user_id}").status_code == 401
    assert client.get(f"/users/{other_user_id}").status_code == 401

    # Admins can get users by their IDs
    make_admin(user_id, cidc_api)
    with cidc_api.app_context():
        other_user = Users.find_by_id(other_user_id)
    res = client.get(f"/users/{other_user_id}")
    assert res.status_code == 200
    assert res.json == UserSchema().dump(other_user)

    # Trying to get a non-existing user yields 404
    res = client.get(f"/users/123212321")
    assert res.status_code == 404


def test_update_user(cidc_api, clean_db, monkeypatch):
    """Check that updating users works as expected."""
    user_id, other_user_id = setup_users(cidc_api, monkeypatch, registered=True)

    with cidc_api.app_context():
        user = Users.find_by_id(user_id)
        other_user = Users.find_by_id(other_user_id)

    client = cidc_api.test_client()

    patch = {"role": "cidc-admin"}

    # Test that non-admins can't modify anyone
    res = client.patch(f"/users/{user.id}")
    assert res.status_code == 401
    res = client.patch(f"/users/{other_user.id}")
    assert res.status_code == 401

    make_admin(user_id, cidc_api)

    # A missing ETag blocks an update
    res = client.patch(f"/users/{other_user.id}")
    assert res.status_code == 428

    # An incorrect ETag blocks an update
    res = client.patch(f"/users/{other_user.id}", headers={"If-Match": "foo"})
    assert res.status_code == 412

    # An admin can successfully update a user
    res = client.patch(
        f"/users/{other_user.id}", headers={"If-Match": other_user._etag}, json=patch
    )
    assert res.status_code == 200
    assert res.json["id"] == other_user.id
    assert res.json["email"] == other_user.email
    assert res.json["role"] == "cidc-admin"
    assert res.json["approval_date"] is not None

    # Trying to update a non-existing user yields 404
    res = client.patch(
        f"/users/123212321", headers={"If-Match": other_user._etag}, json=patch
    )
    assert res.status_code == 404
