"""Utilities for interacting with the Google Cloud Platform APIs."""
import json
import datetime
import re
import warnings
from collections import namedtuple
from concurrent.futures import Future
from typing import List, Tuple, Optional, BinaryIO

import requests
from google.cloud import storage, pubsub

from ..config.settings import (
    GOOGLE_DOWNLOAD_ROLE,
    GOOGLE_INTAKE_BUCKET,
    GOOGLE_UPLOAD_ROLE,
    GOOGLE_UPLOAD_BUCKET,
    GOOGLE_UPLOAD_TOPIC,
    GOOGLE_DATA_BUCKET,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_EMAILS_TOPIC,
    GOOGLE_PATIENT_SAMPLE_TOPIC,
    GOOGLE_ARTIFACT_UPLOAD_TOPIC,
    GOOGLE_MAX_DOWNLOAD_PERMISSIONS,
    TESTING,
    ENV,
    DEV_CFUNCTIONS_SERVER,
    INACTIVE_USER_DAYS,
)
from ..config.logging import get_logger

logger = get_logger(__name__)


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
        logger.info(
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
    logger.info(f"granting upload to {user_email}")
    bucket = _get_bucket(GOOGLE_UPLOAD_BUCKET)

    # Update the bucket IAM policy to include the user as an uploader.
    policy = bucket.get_iam_policy()
    policy[GOOGLE_UPLOAD_ROLE] = {*policy[GOOGLE_UPLOAD_ROLE], f"user:{user_email}"}
    logger.info(f"{GOOGLE_UPLOAD_ROLE} binding updated to {policy[GOOGLE_UPLOAD_ROLE]}")
    bucket.set_iam_policy(policy)


def revoke_upload_access(user_email: str):
    """
    Revoke a user's upload access for the given bucket.
    """
    logger.info(f"revoking upload from {user_email}")
    bucket = _get_bucket(GOOGLE_UPLOAD_BUCKET)

    # Update the bucket IAM policy to remove the user's uploader privileges.
    policy = bucket.get_iam_policy()
    policy[GOOGLE_UPLOAD_ROLE].discard(f"user:{user_email}")
    logger.info(f"{GOOGLE_UPLOAD_ROLE} binding updated to {policy[GOOGLE_UPLOAD_ROLE]}")
    bucket.set_iam_policy(policy)


def _build_intake_prefix(
    user_id: int, user_email: str, trial_id: str, upload_type: str
) -> str:
    usernameish = user_email.split("@")[0].replace(".", "")
    return (
        f"{_build_trial_upload_prefix(trial_id, upload_type)}/{usernameish}-{user_id}"
    )


def grant_intake_access(
    user_id: int, user_email: str, trial_id: str, upload_type: str
) -> str:
    """
    Give a user upload access to a subdirectory of the intake bucket with prefix like
    <trial id>/<upload type>/<user email prefix>-<user id>

    Return the GCS URI to which access has been granted.
    """
    prefix = _build_intake_prefix(user_id, user_email, trial_id, upload_type)

    logger.info(f"Granting intake access on {prefix} to {user_email}")

    return grant_conditional_gcs_access(
        GOOGLE_INTAKE_BUCKET, prefix, GOOGLE_UPLOAD_ROLE, user_email
    )


def revoke_intake_access(
    user_id: int, user_email: str, trial_id: str, upload_type: str
) -> str:
    """
    Revoke a user's upload access to a subdirectory of the intake bucket with prefix like
    <trial id>/<upload type>/<user email prefix>-<user id>

    Return the GCS URI from which access has been revoked.
    """
    prefix = _build_intake_prefix(user_id, user_email, trial_id, upload_type)

    logger.info(f"Granting intake access on {prefix} to {user_email}")

    return revoke_conditional_gcs_access(
        GOOGLE_INTAKE_BUCKET, prefix, GOOGLE_UPLOAD_ROLE, user_email
    )


user_member = lambda email: f"user:{email}"

intake_subdir_regex = re.compile(
    f'resource.name.startsWith\("projects/_/buckets/{GOOGLE_INTAKE_BUCKET}/objects/(.*?)"\)'
)


def list_intake_access(user_email: str) -> List[str]:
    """
    List the GCS URIs in the intake bucket to which this user has access.
    """
    bucket = _get_bucket(GOOGLE_INTAKE_BUCKET)
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.version = 3

    user_uris = []
    for binding in policy.bindings:
        expression = binding.get("condition", {}).get("expression", "")
        subdir_match = intake_subdir_regex.match(expression)
        if (
            binding["members"] == {user_member(user_email)}
            and binding["role"] == GOOGLE_UPLOAD_ROLE
            and subdir_match
        ):
            user_uris.append(f"gs://{GOOGLE_INTAKE_BUCKET}/{subdir_match.group(1)}")

    return user_uris


def grant_download_access(user_email: str, trial_id: str, upload_type: str) -> str:
    """
    Give a user download access to all objects in a trial of a particular upload type.
    If the user already has download access for this trial and upload type, regrant the
    permission with a new, extended TTL. 
    
    Return the GCS URI to which access has been granted.
    """
    prefix = _build_trial_upload_prefix(trial_id, upload_type)

    logger.info(f"Granting download access on {prefix}* to {user_email}")

    return grant_conditional_gcs_access(
        GOOGLE_DATA_BUCKET, prefix, GOOGLE_DOWNLOAD_ROLE, user_email
    )


def revoke_download_access(user_email: str, trial_id: str, upload_type: str):
    """
    Revoke a user's download access to all objects in a trial of a particular upload type.

    Return the GCS URI from which access has been revoked.
    """
    prefix = _build_trial_upload_prefix(trial_id, upload_type)

    logger.info(f"Revoking download access on {prefix}* to {user_email}")

    return revoke_conditional_gcs_access(
        GOOGLE_DATA_BUCKET, prefix, GOOGLE_DOWNLOAD_ROLE, user_email
    )


def _build_trial_upload_prefix(trial_id: str, upload_type: str) -> str:
    broad_upload_type = upload_type.lower().replace(" ", "_").split("_", 1)[0]
    return f"{trial_id}/{broad_upload_type}"


def grant_conditional_gcs_access(
    bucket_name: str, prefix: str, role: str, user_email: str
) -> str:
    # get the current IAM policy for the provided bucket
    bucket = _get_bucket(bucket_name)
    # see https://cloud.google.com/storage/docs/access-control/using-iam-permissions#code-samples_3
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.version = 3

    # remove the existing binding if one exists so that we can recreate it with
    # an updated TTL.
    _find_and_pop_binding(policy, prefix, role, user_email)
    binding = _build_binding_with_expiry(bucket_name, prefix, role, user_email)

    # (re)insert the binding into the policy
    policy.bindings.append(binding)
    bucket.set_iam_policy(policy)

    return f"gs://{bucket_name}/{prefix}"


def revoke_conditional_gcs_access(
    bucket_name: str, prefix: str, role: str, user_email: str
):
    logger.info(f"Revoking download access on {prefix}* from {user_email}")

    # get the current IAM policy for the data bucket
    bucket = _get_bucket(bucket_name)
    # see https://cloud.google.com/storage/docs/access-control/using-iam-permissions#code-samples_3
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.version = 3

    # find and remove all matching policy bindings for this user if any exist
    for i in range(GOOGLE_MAX_DOWNLOAD_PERMISSIONS):
        removed_binding = _find_and_pop_binding(policy, prefix, role, user_email)
        if removed_binding is None:
            if i == 0:
                warnings.warn(
                    f"Tried to revoke a non-existent download IAM permission for {user_email}/{prefix}"
                )
            break

    bucket.set_iam_policy(policy)

    return f"gs://{bucket_name}/{prefix}"


# Arbitrary upper bound on the number of GCS bindings we expect a user to have
MAX_REVOKE_ALL_ITERATIONS = 250


def revoke_all_download_access(user_email: str):
    """
    Completely revoke a user's download access to all objects in the data bucket.
    """
    # get the current IAM policy for the data bucket
    bucket = _get_bucket(GOOGLE_DATA_BUCKET)
    # see https://cloud.google.com/storage/docs/access-control/using-iam-permissions#code-samples_3
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.version = 3

    # find and pop all download role policy bindings for this user
    for _ in range(MAX_REVOKE_ALL_ITERATIONS):
        # this finds and removes *any* download binding for the given user_email
        if _find_and_pop_binding(policy, "", GOOGLE_DOWNLOAD_ROLE, user_email) is None:
            break

    bucket.set_iam_policy(policy)


def _build_binding_with_expiry(
    bucket: str,
    prefix: str,
    role: str,
    user_email: str,
    ttl_days: int = INACTIVE_USER_DAYS,
) -> dict:
    """
    Grant the user associated with `user_email` the provided IAM `role` when acting
    on objects in `bucket` whose URIs start with `prefix`. This permission remains active
    for `ttl_days` days.

    See GCP common expression language syntax overview: https://cloud.google.com/iam/docs/conditions-overview
    """
    timestamp = datetime.datetime.now()
    expiry_date = (timestamp + datetime.timedelta(ttl_days)).date()
    ttl_clause = f'request.time < timestamp("{expiry_date.isoformat()}T00:00:00Z")'
    prefix_clause = (
        f'resource.name.startsWith("projects/_/buckets/{bucket}/objects/{prefix}")'
    )

    return {
        "role": role,
        "members": {user_member(user_email)},
        "condition": {
            "title": f"{role} access on {prefix} until {expiry_date}",
            "description": f"Auto-updated by the CIDC API on {timestamp}",
            "expression": f"{prefix_clause} && {ttl_clause}",
        },
    }


def _find_and_pop_binding(
    policy: storage.bucket.Policy, prefix: str, role: str, user_email: str
) -> Optional[dict]:
    """
    Find an IAM policy binding for the given `user_email`, `policy`, and `role`, and pop
    it from the policy's bindings list if it exists.
    """
    # try to find the policy binding on the `policy`
    user_binding_index = None
    for i, binding in enumerate(policy.bindings):
        if (
            binding.get("role") == role
            and binding.get("members") == {user_member(user_email)}
            and prefix in binding.get("condition", {}).get("expression", "")
        ):
            # a user should be a member of no more than one conditional download binding
            if user_binding_index is not None:
                warnings.warn(
                    f"Found multiple conditional bindings for {user_email} on {prefix}. This is an invariant violation - "
                    "check out permissions on the CIDC GCS buckets to debug."
                )
                break
            user_binding_index = i

    binding = (
        policy.bindings.pop(user_binding_index)
        if user_binding_index is not None
        else None
    )

    return binding


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
    logger.info(f"generated signed URL for {object_name}: {url}")

    return url


def _encode_and_publish(content: str, topic: str) -> Future:
    """Convert `content` to bytes and publish it to `topic`."""
    pubsub_publisher = pubsub.PublisherClient()
    topic = pubsub_publisher.topic_path(GOOGLE_CLOUD_PROJECT, topic)
    data = bytes(content, "utf-8")

    # Don't actually publish to Pub/Sub if running locally
    if ENV == "dev":
        if DEV_CFUNCTIONS_SERVER:
            logger.info(
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
                logger.info(f"Got {res}")
                if res.status_code != 200:
                    raise Exception(
                        f"Couldn't publish message {content!r} to {DEV_CFUNCTIONS_SERVER}/{topic}: {res!r}"
                    )
        else:
            logger.info(f"Would've published message {content} to topic {topic}")
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
        logger.info(f"Would send email with subject '{subject}' to {to_emails}")
        return

    email_json = json.dumps(
        dict(to_emails=to_emails, subject=subject, html_content=html_content, **kw)
    )

    report = _encode_and_publish(email_json, GOOGLE_EMAILS_TOPIC)

    # Await confirmation that the published message was received.
    if report:
        report.result()
