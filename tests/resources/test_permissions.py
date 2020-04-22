from unittest.mock import MagicMock
from datetime import datetime
from typing import Tuple

from cidc_api.models import (
    Users,
    Permissions,
    PermissionSchema,
    TrialMetadata,
    CIDCRole,
)

from ..utils import mock_current_user, make_admin

TRIAL_ID = "foo"


def setup_permissions(cidc_api, monkeypatch) -> Tuple[int, int]:
    """
    Create two users, one trial, and three permissions in `db`.
    Two permissions will belong to the first user, and the third will
    belong to the second one. Returns the first and second user ids 
    as a tuple.
    """
    current_user = Users(
        id=1,
        email="test@email.com",
        role=CIDCRole.CIMAC_USER.value,
        approval_date=datetime.now(),
    )
    other_user = Users(id=2, email="other@email.org")

    mock_current_user(current_user, monkeypatch)

    with cidc_api.app_context():
        # Create users
        current_user.insert()
        other_user.insert()

        # Create trial
        TrialMetadata.create(TRIAL_ID, {})

        # Create permissions
        def create_permission(uid, assay):
            Permissions(
                granted_by_user=uid,
                granted_to_user=uid,
                trial_id=TRIAL_ID,
                upload_type=assay,
            ).insert()

        create_permission(current_user.id, "wes")
        create_permission(current_user.id, "olink")
        create_permission(other_user.id, "olink")

        return current_user.id, other_user.id


def test_list_permissions(cidc_api, clean_db, monkeypatch):
    """Check that listing permissions works as expected."""
    current_user_id, other_user_id = setup_permissions(cidc_api, monkeypatch)

    client = cidc_api.test_client()

    # Check that user can get their own permissions
    res = client.get("permissions")
    assert res.status_code == 200
    assert len(res.json) == 2
    for perm in res.json:
        assert perm["granted_to_user"] == current_user_id

    # Check that a non-admin user can't get another user's permissions
    res = client.get(f"permissions?user_id={other_user_id}")
    assert res.status_code == 401
    assert "cannot view permissions for other users" in res.json["message"]

    # Check that an admin can read the other user's permissions
    make_admin(current_user_id, cidc_api)
    res = client.get(f"permissions?user_id={other_user_id}")
    assert res.status_code == 200
    assert len(res.json) == 1


def test_get_permission(cidc_api, clean_db, monkeypatch):
    """Check that getting a single permission by ID works as expected."""
    current_user_id, other_user_id = setup_permissions(cidc_api, monkeypatch)

    with cidc_api.app_context():
        current_user_perm = Permissions.find_for_user(current_user_id)[0]
        other_user_perm = Permissions.find_for_user(other_user_id)[0]

    client = cidc_api.test_client()

    # Check that getting a permission that doesn't exist yields 404
    res = client.get("permissions/123212321")
    assert res.status_code == 404

    # Check that a non-admin getting another user's permission yields 404
    res = client.get(f"permissions/{other_user_perm.id}")
    assert res.status_code == 404

    # Check that a non-admin can get their own permission
    res = client.get(f"permissions/{current_user_perm.id}")
    assert res.status_code == 200
    assert res.json == PermissionSchema().dump(current_user_perm)

    # Check that an admin can get another user's permission
    make_admin(current_user_id, cidc_api)
    res = client.get(f"permissions/{other_user_perm.id}")
    assert res.status_code == 200
    assert res.json == PermissionSchema().dump(other_user_perm)


def test_create_permission(cidc_api, clean_db, monkeypatch):
    """Check that creating a new permission works as expected."""
    current_user_id, other_user_id = setup_permissions(cidc_api, monkeypatch)

    with cidc_api.app_context():
        current_user = Users.find_by_id(current_user_id)

    client = cidc_api.test_client()

    # Non-admins should be blocked from posting to this endpoint
    res = client.post("permissions")
    assert res.status_code == 401
    assert "not authorized to access this endpoint" in res.json["message"]

    # Admins should be able to create new permissions
    make_admin(current_user_id, cidc_api)
    perm = {
        "granted_to_user": other_user_id,
        "trial_id": TRIAL_ID,
        "upload_type": "bar",
    }
    res = client.post("permissions", json=perm)
    assert res.status_code == 201
    assert "id" in res.json
    assert {**res.json, **perm} == res.json
    with cidc_api.app_context():
        assert Permissions.find_by_id(res.json["id"])

    # Re-insertion is not allowed
    res = client.post("permissions", json=perm)
    assert res.status_code == 400
    assert "user, trial, and upload type already exists." in res.json["message"]


def test_delete_permission(cidc_api, clean_db, monkeypatch):
    """Check that deleting a permission works as expected."""
    current_user_id, other_user_id = setup_permissions(cidc_api, monkeypatch)

    with cidc_api.app_context():
        perm = Permissions.find_for_user(current_user_id)[0]

    client = cidc_api.test_client()

    # Non-admins are not allowed to delete
    res = client.delete(f"permissions/{perm.id}")
    assert res.status_code == 401
    assert "not authorized to access this endpoint" in res.json["message"]

    make_admin(current_user_id, cidc_api)

    # Requester must supply an If-Match header
    res = client.delete(f"permissions/{perm.id}")
    assert res.status_code == 428

    headers = {"If-Match": "foobar"}

    # Returns NotFound if no record exists
    res = client.delete(f"permissions/1232123", headers=headers)
    assert res.status_code == 404

    # A mismatched ETag leads to a PreconditionFailed error
    res = client.delete(f"permissions/{perm.id}", headers=headers)
    assert res.status_code == 412

    # A matching ETag leads to a successful deletion
    headers["If-Match"] = perm._etag
    res = client.delete(f"permissions/{perm.id}", headers=headers)
    assert res.status_code == 200
    with cidc_api.app_context():
        assert Permissions.find_by_id(perm.id) is None
