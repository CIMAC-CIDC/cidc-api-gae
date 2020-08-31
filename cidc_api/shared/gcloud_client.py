"""Utilities for interacting with the Google Cloud Platform APIs."""
import json
import datetime
from collections import namedtuple
from concurrent.futures import Future
from typing import List, Tuple
from typing.io import BinaryIO

import requests

from google.cloud import storage, pubsub

from ..config.settings import (
    GOOGLE_DOWNLOAD_ROLE,
    GOOGLE_UPLOAD_ROLE,
    GOOGLE_UPLOAD_BUCKET,
    GOOGLE_UPLOAD_TOPIC,
    GOOGLE_DATA_BUCKET,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_EMAILS_TOPIC,
    GOOGLE_PATIENT_SAMPLE_TOPIC,
    GOOGLE_ARTIFACT_UPLOAD_TOPIC,
    TESTING,
    ENV,
    DEV_CFUNCTIONS_SERVER,
    INACTIVE_USER_DAYS,
)


def _get_bucket(bucket_name: str) -> storage.Bucket:
    """Get the bucket with name `bucket_name` from GCS."""
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    return bucket


_xlsx_gcs_uri_format = (
    "{trial_id}/xlsx/{template_category}/{template_type}/{upload_moment}.xlsx"
)


_pseudo_blob = namedtuple(
    "_pseudo_blob", ["name", "size", "md5_hash", "crc32c", "time_created"]
)


def upload_xlsx_to_gcs(
    trial_id: str,
    template_category: str,
    template_type: str,
    filebytes: BinaryIO,
    upload_moment: str,
):
    """
    Upload an xlsx template file to GCS, returning the object URI.
    
    `template_category` is either "manifests" or "assays".
    `template_type` is an assay or manifest type, like "wes" or "pbmc" respectively.

    Returns:
        arg1: GCS blob object
    """
    blob_name = _xlsx_gcs_uri_format.format(
        trial_id=trial_id,
        template_category=template_category,
        template_type=template_type,
        upload_moment=upload_moment,
    )

    if ENV == "dev":
        print(
            f"Would've saved {blob_name} to {GOOGLE_UPLOAD_BUCKET} and {GOOGLE_DATA_BUCKET}"
        )
        return _pseudo_blob(
            blob_name, 0, "_pseudo_md5_hash", "_pseudo_crc32c", upload_moment
        )

    upload_bucket: storage.Bucket = _get_bucket(GOOGLE_UPLOAD_BUCKET)
    blob = upload_bucket.blob(blob_name)

    filebytes.seek(0)
    blob.upload_from_file(filebytes)

    data_bucket = _get_bucket(GOOGLE_DATA_BUCKET)
    final_object = upload_bucket.copy_blob(blob, data_bucket)

    return final_object


def grant_upload_access(user_email: str):
    """
    Grant a user upload access to the GOOGLE_UPLOAD_BUCKET. Upload access
    means a user can write objects to the bucket but cannot delete,
    overwrite, or read objects from this bucket.
    """
    print(f"granting upload to {user_email}")
    bucket = _get_bucket(GOOGLE_UPLOAD_BUCKET)

    # Update the bucket IAM policy to include the user as an uploader.
    policy = bucket.get_iam_policy()
    policy[GOOGLE_UPLOAD_ROLE] = {*policy[GOOGLE_UPLOAD_ROLE], f"user:{user_email}"}
    print(f"{GOOGLE_UPLOAD_ROLE} binding updated to {policy[GOOGLE_UPLOAD_ROLE]}")
    bucket.set_iam_policy(policy)


def revoke_upload_access(user_email: str):
    """
    Revoke a user's upload access for the given bucket.
    """
    print(f"revoking upload from {user_email}")
    bucket = _get_bucket(GOOGLE_UPLOAD_BUCKET)

    # Update the bucket IAM policy to remove the user's uploader privileges.
    policy = bucket.get_iam_policy()
    policy[GOOGLE_UPLOAD_ROLE].discard(f"user:{user_email}")
    print(f"{GOOGLE_UPLOAD_ROLE} binding updated to {policy[GOOGLE_UPLOAD_ROLE]}")
    bucket.set_iam_policy(policy)


def grant_download_access(user_email: str, trial_id: str, upload_type: str):
    """
    Give a user download access to all objects in a trial of a particular upload type.
    """
    member_id = f"user:{user_email}"
    url_prefix, prefix_expression = _get_prefix_expression(trial_id, upload_type)
    ttl_expression = _get_ttl_expression()

    print(f"Granting download access on {url_prefix}* to {user_email}")

    # get the current IAM policy for the data bucket
    bucket = _get_bucket(GOOGLE_DATA_BUCKET)
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.version = 3

    # check if a binding for this user/trial/upload_type combo already exists
    binding_exists = False
    for binding in policy.bindings:
        if _is_matching_conditional_binding(binding, member_id, prefix_expression):
            binding_exists = True
            break

    # if the binding doesn't exist, create it
    if not binding_exists:
        policy.bindings.append(
            {
                "role": GOOGLE_DOWNLOAD_ROLE,
                "members": {member_id},
                "condition": {
                    "title": f"Download access on {url_prefix}* for {user_email}",
                    "description": f"Auto-generated by the CIDC API on {datetime.datetime.now()}",
                    "expression": f"{prefix_expression} && {ttl_expression}",
                },
            }
        )

    bucket.set_iam_policy(policy)


def revoke_download_access(user_email: str, trial_id: str, upload_type: str):
    """
    Revoke a user's download access to all objects in a trial of a particular upload type.
    """
    member_id = f"user:{user_email}"
    url_prefix, prefix_expression = _get_prefix_expression(trial_id, upload_type)

    print(f"Revoking download access on {url_prefix}* from {user_email}")

    # get the current IAM policy for the data bucket
    bucket = _get_bucket(GOOGLE_DATA_BUCKET)
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.version = 3

    # find the index of the binding for this user/trial/upload_type combo
    clean_bindings = []
    for binding in policy.bindings:
        if not _is_matching_conditional_binding(binding, member_id, prefix_expression):
            clean_bindings.append(binding)

    policy.bindings = clean_bindings
    bucket.set_iam_policy(policy)


def _get_prefix_expression(trial_id: str, upload_type: str) -> Tuple[str, str]:
    """
    Build the object URL prefix and CEL IAM condition for restricting downloads to objects 
    belonging to the given trial_id and upload_type.

    See: https://cloud.google.com/storage/docs/access-control/iam#conditions
    """
    # convert, e.g., wes_bam -> wes or cytof_analysis -> cytof
    broad_upload_type = upload_type.split("_", 1)[0]

    # build the prefix check expression
    url_prefix = f"{trial_id}/{broad_upload_type}"
    prefix_expression = f'resource.name.startsWith("projects/_/buckets/{GOOGLE_DATA_BUCKET}/objects/{url_prefix}")'

    return url_prefix, prefix_expression


def _get_ttl_expression(days_until_expiry: int = INACTIVE_USER_DAYS) -> str:
    """
    Build the time-to-live CEL IAM condition for restricting GCS download permissions' lifetimes
    to `days_until_expiry` days.
    """
    grant_until_date = (
        (datetime.datetime.now() + datetime.timedelta(days_until_expiry))
        .date()
        .isoformat()
    )
    ttl_expression = f'request.time < timestamp("{grant_until_date}T00:00:00Z")'
    return ttl_expression


def _is_matching_conditional_binding(
    binding: storage.bucket.Policy, member_id: str, subexpression: str
) -> bool:
    try:
        has_user = binding["members"] == {member_id}
        has_condition = subexpression in binding["condition"]["expression"]
        return has_user and has_condition
    except KeyError:
        return False


def get_signed_url(
    object_name: str,
    bucket_name: str = GOOGLE_DATA_BUCKET,
    method: str = "GET",
    expiry_mins: int = 30,
) -> str:
    """
    Generate a signed URL for `object_name` to give a client temporary access.

    Using v2 signed urls because v4 is in Beta and response_disposition doesn't work.
    https://cloud.google.com/storage/docs/access-control/signing-urls-with-helpers
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(object_name)

    # Generate the signed URL, allowing a client to use `method` for `expiry_mins` minutes
    expiration = datetime.timedelta(minutes=expiry_mins)
    full_filename = object_name.replace("/", "_").replace('"', "_").replace(" ", "_")
    url = blob.generate_signed_url(
        version="v2",
        expiration=expiration,
        method=method,
        response_disposition=f'attachment; filename="{full_filename}"',
    )
    print(f"generated signed URL for {object_name}: {url}")

    return url


def _encode_and_publish(content: str, topic: str) -> Future:
    """Convert `content` to bytes and publish it to `topic`."""
    pubsub_publisher = pubsub.PublisherClient()
    topic = pubsub_publisher.topic_path(GOOGLE_CLOUD_PROJECT, topic)
    data = bytes(content, "utf-8")

    # Don't actually publish to Pub/Sub if running locally
    if ENV == "dev":
        if DEV_CFUNCTIONS_SERVER:
            print(
                f"Publishing message {content!r} to topic {DEV_CFUNCTIONS_SERVER}/{topic}"
            )
            import base64

            bdata = base64.b64encode(content.encode("utf-8"))
            try:
                res = requests.post(
                    f"{DEV_CFUNCTIONS_SERVER}/{topic}", data={"data": bdata}
                )
            except Exception as e:
                raise Exception(
                    f"Couldn't publish message {content!r} to topic {DEV_CFUNCTIONS_SERVER}/{topic}"
                ) from e
            else:
                print(f"Got {res}")
                if res.status_code != 200:
                    raise Exception(
                        f"Couldn't publish message {content!r} to {DEV_CFUNCTIONS_SERVER}/{topic}: {res!r}"
                    )
        else:
            print(f"Would've published message {content} to topic {topic}")
        return

    # The Pub/Sub publisher client returns a concurrent.futures.Future
    # containing info about whether the publishing was successful.
    report = pubsub_publisher.publish(topic, data=data)

    return report


def publish_upload_success(job_id: int):
    """Publish to the uploads topic that the upload job with the provided `job_id` succeeded."""
    report = _encode_and_publish(str(job_id), GOOGLE_UPLOAD_TOPIC)

    # For now, we wait await this Future. Going forward, maybe
    # we should look for a way to leverage asynchrony here.
    if report:
        report.result()


def publish_patient_sample_update(manifest_upload_id: int):
    """Publish to the patient_sample_update topic that a new manifest has been uploaded."""
    report = _encode_and_publish(str(manifest_upload_id), GOOGLE_PATIENT_SAMPLE_TOPIC)

    # Wait for response from pub/sub
    if report:
        report.result()


def publish_artifact_upload(file_id: int):
    """Publish a downloadable file ID to the artifact_upload topic"""
    report = _encode_and_publish(str(file_id), GOOGLE_ARTIFACT_UPLOAD_TOPIC)

    # Wait for response from pub/sub
    if report:
        report.result()


def send_email(to_emails: List[str], subject: str, html_content: str, **kw):
    """
    Publish an email-to-send to the emails topic.
    `kw` are expected to be sendgrid json api style additional email parameters. 
    """
    # Don't actually send an email if this is a test
    if TESTING or ENV == "dev":
        print(f"Would send email with subject '{subject}' to {to_emails}")
        return

    email_json = json.dumps(
        dict(to_emails=to_emails, subject=subject, html_content=html_content, **kw)
    )

    report = _encode_and_publish(email_json, GOOGLE_EMAILS_TOPIC)

    # Await confirmation that the published message was received.
    if report:
        report.result()
