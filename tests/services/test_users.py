NEW_USERS = "new_users"
USERS = "users"

EMAIL = "test@email.com"
AUTH_HEADER = {"Authorization": "Bearer foo"}

profile = {"email": EMAIL}
other_profile = {"email": "foo@bar.org"}


def fake_token_auth(*args):
    return profile


def test_enforce_self_creation(app, db, monkeypatch):
    """Check that users can only create themselves"""
    monkeypatch.setattr(app.auth, "token_auth", fake_token_auth)

    client = app.test_client()

    # If there's a mismatch between the requesting user's email
    # and the email of the user to create, the user should not be created
    response = client.post(NEW_USERS, json=other_profile, headers=AUTH_HEADER)
    assert response.status_code == 401
    assert "not authorized to create use" in response.json["_error"]["message"]

    # Self-creation should work just fine
    response = client.post(NEW_USERS, json=profile, headers=AUTH_HEADER)
    assert response.status_code == 201  # Created


def test_prevent_unregistered_lookup(app, db, monkeypatch):
    """Check that unregistered users can only lookup themselves"""
    monkeypatch.setattr(app.auth, "token_auth", fake_token_auth)

    client = app.test_client()

    # Create two new users
    client.post(NEW_USERS, json=profile, headers=AUTH_HEADER)
    client.post(NEW_USERS, json=other_profile, headers=AUTH_HEADER)

    # Check that a user can only look themselves up
    response = client.get(USERS, headers=AUTH_HEADER)
    assert response.status_code == 200
    users = response.json["_items"]
    assert len(users) == 1
    assert users[0]["email"] == profile["email"]

    filtered_response = client.get(
        USERS + '?where{"email": "%s"}' % EMAIL, headers=AUTH_HEADER
    )
    assert filtered_response.status_code == 200
    assert filtered_response.json["_items"] == response.json["_items"]

    # If the user tries to look up someone else, they get nothing back
    response = client.get(
        USERS + '?where={"email": "%s"}' % other_profile["email"], headers=AUTH_HEADER
    )
    assert response.status_code == 200
    assert len(response.json["_items"]) == 0

    # TODO: test that admins can still list all users
