from gcs_iam import grant_write_access, revoke_write_access

EMAIL = "test@email.com"


class FakeBlob:
    def __init__(self, *args):
        pass


def test_grant_write(monkeypatch):
    class GrantBlob(FakeBlob):
        def get_iam_policy(self):
            return {"roles/storage.objectCreator": set()}

        def set_iam_policy(self, policy):
            assert f"user:{EMAIL}" in policy["roles/storage.objectCreator"]

    monkeypatch.setattr("gcs_iam._get_or_create_blob", GrantBlob)
    grant_write_access("foo", "bar", EMAIL)


def test_revoke_write(monkeypatch):
    class RevokeBlob(FakeBlob):
        def get_iam_policy(self):
            return {"roles/storage.objectCreator": set(EMAIL)}

        def set_iam_policy(self, policy):
            assert EMAIL not in policy["roles/storage.objectCreator"]

    monkeypatch.setattr("gcs_iam._get_or_create_blob", RevokeBlob)
    revoke_write_access("foo", "bar", EMAIL)
