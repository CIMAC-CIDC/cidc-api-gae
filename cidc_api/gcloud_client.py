"""Utilities for interacting with the Google Cloud Platform APIs."""
import json
import datetime
from concurrent.futures import Future
from typing import List
from typing.io import BinaryIO

from google.cloud import storage
from google.cloud import pubsub

from config.settings import (
    GOOGLE_UPLOAD_ROLE,
    GOOGLE_UPLOAD_BUCKET,
    GOOGLE_UPLOAD_TOPIC,
    GOOGLE_DATA_BUCKET,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_EMAILS_TOPIC,
    TESTING,
    ENV,
)


def _get_bucket(bucket_name: str) -> storage.Bucket:
    """Get the bucket with name `bucket_name` from GCS."""
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    return bucket


def _iam_id(user_email: str) -> str:
    """Append the appropriate IAM account type to a user's email"""
    return f"user:{user_email}"


def upload_xlsx_to_gcs(
    trial_id: str, template_type: str, filename: str, filebytes: BinaryIO
) -> str:
    """Upload an xlsx template file to GCS, returning the object URI."""
    upload_moment = datetime.datetime.now()
    blob_name = f"xlsx/{trial_id}/{template_type}/{filename}/{upload_moment}"

    bucket: storage.Bucket = _get_bucket(GOOGLE_UPLOAD_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_file(filebytes)
    return blob_name


def grant_upload_access(bucket_name: str, user_email: str):
    """
    Grant a user upload access to the given bucket. Upload access
    means a user can write objects to the bucket but cannot delete,
    overwrite, or read objects from this bucket.
    """
    bucket = _get_bucket(bucket_name)

    # Update the bucket IAM policy to include the user as an uploader.
    policy = bucket.get_iam_policy()
    policy[GOOGLE_UPLOAD_ROLE].add(_iam_id(user_email))
    bucket.set_iam_policy(policy)


def revoke_upload_access(bucket_name: str, user_email: str):
    """
    Revoke a user's upload access for the given bucket.
    """
    bucket = _get_bucket(bucket_name)

    # Update the bucket IAM policy to remove the user's uploader privileges.
    policy = bucket.get_iam_policy()
    policy[GOOGLE_UPLOAD_ROLE].discard(_iam_id(user_email))
    bucket.set_iam_policy(policy)


def get_signed_url(
    object_name: str,
    bucket_name: str = GOOGLE_DATA_BUCKET,
    method: str = "GET",
    expiry_mins: int = 30,
) -> str:
    """
    Generate a signed URL for `object_name` to give a client temporary access.

    See: https://cloud.google.com/storage/docs/access-control/signing-urls-with-helpers
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(object_name)

    # Generate the signed URL, allowing a client to use `method` for `expiry_mins` minutes
    expiration = datetime.timedelta(minutes=expiry_mins)
    url = blob.generate_signed_url(version="v4", expiration=expiration, method=method)

    return url


def _encode_and_publish(content: str, topic: str) -> Future:
    """Convert `content` to bytes and publish it to `topic`."""
    pubsub_publisher = pubsub.PublisherClient()
    topic = pubsub_publisher.topic_path(GOOGLE_CLOUD_PROJECT, topic)
    data = bytes(content, "utf-8")

    # The Pub/Sub publisher client returns a concurrent.futures.Future
    # containing info about whether the publishing was successful.
    report = pubsub_publisher.publish(topic, data=data)

    return report


def publish_upload_success(job_id: int):
    """Publish to the uploads topic that the upload job with the provided `job_id` succeeded."""
    report = _encode_and_publish(str(job_id), GOOGLE_UPLOAD_TOPIC)

    # For now, we wait await this Future. Going forward, maybe
    # we should look for a way to leverage asynchrony here.
    report.result()


def send_email(to_emails: List[str], subject: str, html_content: str):
    """Publish an email-to-send to the emails topic."""
    # Don't actually send an email if this is a test
    if TESTING or ENV == "dev":
        print(f"Would send email with subject '{subject}' to {to_emails}")
        return

    email_json = json.dumps(
        {"to_emails": to_emails, "subject": subject, "html_content": html_content}
    )

    report = _encode_and_publish(email_json, GOOGLE_EMAILS_TOPIC)

    # Await confirmation that the published message was received.
    report.result()
