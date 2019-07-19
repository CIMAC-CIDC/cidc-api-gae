from gcs_iam import grant_write_access, revoke_write_access
from settings import GOOGLE_UPLOAD_ROLE

EMAIL = "test@email.com"


class FakeBlob:
    def __init__(self, *args):
        pass


def test_grant_write(monkeypatch):
    class GrantBlob(FakeBlob):
        def get_iam_policy(self):
            return {GOOGLE_UPLOAD_ROLE: set()}

        def set_iam_policy(self, policy):
            assert f"user:{EMAIL}" in policy[GOOGLE_UPLOAD_ROLE]

    monkeypatch.setattr("gcs_iam._get_or_create_blob", GrantBlob)
    grant_write_access("foo", "bar", EMAIL)


def test_revoke_write(monkeypatch):
    class RevokeBlob(FakeBlob):
        def get_iam_policy(self):
            return {GOOGLE_UPLOAD_ROLE: set(EMAIL)}

        def set_iam_policy(self, policy):
            assert EMAIL not in policy[GOOGLE_UPLOAD_ROLE]

    monkeypatch.setattr("gcs_iam._get_or_create_blob", RevokeBlob)
    revoke_write_access("foo", "bar", EMAIL)
