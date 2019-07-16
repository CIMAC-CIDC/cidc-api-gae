"""Utilities for managing access to GCS objects."""

from google.cloud import storage

OBJECT_WRITE_ROLE = "roles/storage.objectCreator"


def _get_or_create_blob(bucket_name: str, object_name: str):
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(object_name)
    return blob


def grant_write_access(bucket_name: str, object_name: str, user_email: str):
    """
    Grant a user write access to gs://`bucket_name`/`object_name`, creating the object
    if it doesn't exist already.
    """
    blob = _get_or_create_blob(bucket_name, object_name)

    # Update the IAM policy
    policy = blob.get_iam_policy()
    policy[OBJECT_WRITE_ROLE].add(user_email)
    blob.set_iam_policy(policy)


def revoke_write_access(bucket_name: str, object_name: str, user_email: str):
    """
    Revoke a user's write access to gs://`bucket_name`/`object_name`.
    """
    blob = _get_or_create_blob(bucket_name, object_name)

    # Update the IAM policy
    policy = blob.get_iam_policy()
    policy[OBJECT_WRITE_ROLE].discard(user_email)
    blob.set_iam_policy(policy)
