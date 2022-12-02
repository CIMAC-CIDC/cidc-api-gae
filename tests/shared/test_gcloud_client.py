import json
import os
import re

os.environ["TZ"] = "UTC"
from io import BytesIO
from unittest.mock import call, MagicMock
from datetime import datetime
from typing import List

from werkzeug.datastructures import FileStorage
from google.api_core.iam import Policy
from google.cloud.bigquery.enums import EntityTypes
from google.cloud import bigquery

from cidc_schemas import prism
from cidc_api.shared import gcloud_client
from cidc_api.config import settings
from cidc_api.shared.gcloud_client import (
    create_intake_bucket,
    get_blob_names,
    grant_download_access,
    grant_download_access_to_blob_names,
    grant_lister_access,
    grant_upload_access,
    grant_bigquery_iam_access,
    refresh_intake_access,
    revoke_all_download_access,
    revoke_bigquery_iam_access,
    revoke_download_access_from_blob_names,
    revoke_download_access,
    revoke_intake_access,
    revoke_lister_access,
    revoke_upload_access,
    upload_xlsx_to_gcs,
    upload_xlsx_to_intake_bucket,
    _build_storage_iam_binding,
    _build_trial_upload_prefixes,
    _pseudo_blob,
    _xlsx_gcs_uri_format,
)
from cidc_api.config.settings import (
    GOOGLE_ACL_DATA_BUCKET,
    GOOGLE_GRANT_DOWNLOAD_PERMISSIONS_TOPIC,
    GOOGLE_INTAKE_BUCKET,
    GOOGLE_INTAKE_ROLE,
    GOOGLE_LISTER_ROLE,
    GOOGLE_UPLOAD_BUCKET,
    GOOGLE_UPLOAD_ROLE,
    GOOGLE_BIGQUERY_USER_ROLE,
)

ID = 123
EMAIL = "test.user@email.com"


def _mock_gcloud_storage_client(
    monkeypatch, iam_bindings=[], set_iam_policy_fn=None
) -> MagicMock:
    """
    Mocks google.cloud.storage and google.cloud.storage.Client, returning the client
    Mocks both IAM- and ACL-related functions
    While IAM parameters are explicitly passed for background bindings and a check function,
        ACL checks are performed by checking calls to b.acl.[grant/revoke]_[role] for b in the returned mock_client.blobs
        mock_client.list_blobs returns [mock_client.blobs[0]] if prefix == "10021/wes" else mock_client.blobs

    Parameters
    ----------
    monkeypatch
        needed for mocking
    iam_bindings : List[{"role": str, "members": List[str]}] = []
        returned by [Blob/Bucket].get_iam_policy
        mocks the google return of the existing bindings on the objects
    set_iam_policy_fn : Callable = None
        single arg will be the updated IAM policy, in the form {str role: List[str member]}
        use to assert that changes have been made while also mocking google call

    Returns
    -------
    mock_client : MagicMock
        the return value mocked mocking `gcloud_client._get_storage_client`
        ACL checks are performed by checking calls to b.acl.[grant/revoke]_[role] for b in the mock_client.blobs
        mock_client.list_blobs returns [mock_client.blobs[0]] if prefix == "10021/wes" else mock_client.blobs
    """
    api_request = MagicMock()
    monkeypatch.setattr(
        "google.cloud.storage.blob.Blob.get_iam_policy", lambda *a, **kw: api_request
    )

    def set_iam_policy(self, policy):
        set_iam_policy_fn(policy)

    monkeypatch.setattr("google.cloud.storage.blob.Blob.set_iam_policy", set_iam_policy)
    monkeypatch.setattr(
        "google.cloud.storage.bucket.Bucket.set_iam_policy", set_iam_policy
    )

    # mocking `google.cloud.storage.Client()` to not actually create a client
    # mock ACL-related `client.list_blobs` to return fake objects entirely
    # mock ACL-related `client.get_blob` to return first fake blob
    mock_client = MagicMock(name="mock_client")
    mock_client.blobs = [
        MagicMock(),
        MagicMock(),
    ]

    mock_client.blob_users = [
        MagicMock(),
        MagicMock(),
    ]
    mock_client.blobs[0].acl.user.return_value = mock_client.blob_users[0]
    mock_client.blobs[1].acl.user.return_value = mock_client.blob_users[1]

    def mock_list_blobs(*a, prefix: str = "", **kw):
        if prefix == "10021/wes/":
            return [mock_client.blobs[0]]
        else:
            return mock_client.blobs

    mock_client.list_blobs = mock_list_blobs
    # then check calls to b.acl.[grant/revoke]_[role] for b in mock_client.blobs
    # note the return value mock_client.list_blobs depends solely on the `prefix` kwargs

    mock_client.encode_and_publish = MagicMock()
    monkeypatch.setattr(
        gcloud_client,
        "_encode_and_publish",
        mock_client.encode_and_publish,
    )

    mock_bucket = MagicMock(name="mock_bucket")
    mock_policy = MagicMock(name="policy")
    mock_policy.bindings = iam_bindings
    mock_bucket.get_iam_policy.return_value = mock_policy
    mock_bucket.set_iam_policy = lambda policy: set_iam_policy(None, policy)
    mock_client.bucket.return_value = mock_bucket

    # mocking `gcloud_client._get_storage_client` to not actually create a client
    monkeypatch.setattr(
        gcloud_client, "_get_storage_client", lambda *a, **kw: mock_client
    )

    return mock_client


def _mock_gcloud_bigquery_client(
    monkeypatch,
    access_entry=List[bigquery.AccessEntry],
    set_iam_policy_fn=None,
    update_dataset_fn=None,
) -> None:
    """
    Mocks the crm_service, bigquery_client, and bigquery dataset

    Parameters
    ----------
    monkeypatch
        needed for mocking
    access_entry : List[bigquery.AccessEntry]
        returned by dataset.acess_entries
        mocks the google return of the existing access entries on the objects
    set_iam_policy_fn : Callable = None
        single arg will be the updated IAM policy and project to updaate
        use to assert that changes have been made while also mocking google call
    update_dataset_fn : Callable = None
        single arg will be the updated IAM dataset and element to be updated
        use to assert that changes have been made while also mocking google call
    """
    # mocking _get_crm_service to not actually get a service
    mock_crm = MagicMock()
    monkeypatch.setattr(gcloud_client, "_crm_service", mock_crm)
    projects = MagicMock()
    mock_crm.projects.return_value = projects
    # setIamPolicy = MagicMock()
    # projects.setIamPolicy = setIamPolicy

    def set_iam_policy(resource, body):
        set_iam_policy_fn(resource, body)
        return MagicMock()

    monkeypatch.setattr(projects, "setIamPolicy", set_iam_policy)

    mock_bq_client = MagicMock()
    monkeypatch.setattr(gcloud_client, "_bigquery_client", mock_bq_client)

    def update_dataset(dataset, element):
        update_dataset_fn(dataset, element)

    monkeypatch.setattr(mock_bq_client, "update_dataset", update_dataset)

    mock_dataset = MagicMock(name="dataset")
    mock_dataset.access_entries = access_entry

    monkeypatch.setattr(
        gcloud_client, "_get_bigquery_dataset", lambda *a, **kw: mock_dataset
    )


def test_build_trial_upload_prefixes(clean_db, cidc_api):
    fake_trial_ids = ["foo", "bar", "baz"]

    from cidc_api.models.models import TrialMetadata

    with cidc_api.app_context():
        for trial_id in fake_trial_ids:
            TrialMetadata(
                trial_id=trial_id,
                metadata_json={
                    prism.PROTOCOL_ID_FIELD_NAME: trial_id,
                    "participants": [],
                    "allowed_cohort_names": ["Arm_Z"],
                    "allowed_collection_event_names": [],
                },
            ).insert(session=clean_db)

        assert set(
            _build_trial_upload_prefixes(None, "rna_bam", session=clean_db)
        ) == set(f"{t}/rna/" for t in fake_trial_ids)

    assert _build_trial_upload_prefixes("foo", None) == {
        "foo/atacseq/",
        "foo/ctdna/",
        "foo/cytof/",
        "foo/cytof_analysis/",
        "foo/elisa/",
        "foo/hande/",
        "foo/ihc/",
        "foo/mibi/",
        "foo/microbiome/",
        "foo/mif/",
        "foo/misc_data/",
        "foo/nanostring/",
        "foo/olink/",
        "foo/participants/",
        "foo/rna/",
        "foo/samples/",
        "foo/tcr/",
        "foo/tcr_analysis/",
        "foo/wes/",
        "foo/wes_tumor_only/",
    }
    assert _build_trial_upload_prefixes("foo", "rna_bam") == {"foo/rna/"}


def test_grant_lister_access(monkeypatch):
    """Check that grant_lister_access adds policy bindings as expected"""

    def set_iam_policy(policy):
        assert len(policy.bindings) == 2, str(policy.bindings)
        assert all(b["role"] == GOOGLE_LISTER_ROLE for b in policy.bindings)
        assert any("user:rando" in b["members"] for b in policy.bindings)
        assert any(f"user:{EMAIL}" in b["members"] for b in policy.bindings)
        assert all("condition" not in b for b in policy.bindings)

    _mock_gcloud_storage_client(
        monkeypatch,
        [
            {"role": GOOGLE_LISTER_ROLE, "members": {"user:rando"}},
        ],
        set_iam_policy,
    )

    grant_lister_access(EMAIL)

    _mock_gcloud_storage_client(
        monkeypatch,
        [
            {"role": GOOGLE_LISTER_ROLE, "members": {"user:rando"}},
            {"role": GOOGLE_LISTER_ROLE, "members": {f"user:{EMAIL}"}},
        ],
        set_iam_policy,
    )

    grant_lister_access(EMAIL)


def test_revoke_lister_access(monkeypatch):
    """Check that grant_lister_access adds policy bindings as expected"""

    def set_iam_policy(policy):
        assert len(policy.bindings) == 1
        assert all(b["role"] == GOOGLE_LISTER_ROLE for b in policy.bindings)
        assert any("user:rando" in b["members"] for b in policy.bindings)
        assert all(f"user:{EMAIL}" not in b["members"] for b in policy.bindings)
        assert all("condition" not in b for b in policy.bindings)

    _mock_gcloud_storage_client(
        monkeypatch,
        [
            {"role": GOOGLE_LISTER_ROLE, "members": {"user:rando"}},
            {"role": GOOGLE_LISTER_ROLE, "members": {f"user:{EMAIL}"}},
        ],
        set_iam_policy,
    )

    revoke_lister_access(EMAIL)

    _mock_gcloud_storage_client(
        monkeypatch,
        [
            {"role": GOOGLE_LISTER_ROLE, "members": {"user:rando"}},
        ],
        set_iam_policy,
    )

    revoke_lister_access(EMAIL)


def test_grant_upload_access(monkeypatch):
    def set_iam_policy(policy):
        assert len(policy.bindings) == 2
        assert f"user:rando" in policy.bindings[0]["members"]
        assert f"user:{EMAIL}" in policy.bindings[1]["members"]

    _mock_gcloud_storage_client(
        monkeypatch,
        [{"role": GOOGLE_UPLOAD_ROLE, "members": ["user:rando"]}],
        set_iam_policy,
    )

    grant_upload_access(EMAIL)


def test_grant_bigquery_access(monkeypatch):
    def set_iam_policy(resource, body):
        assert resource == "cidc-dfci-staging"
        assert f"user:rando" in body["policy"]["bindings"][0]["members"]
        assert f"user:{EMAIL}" in body["policy"]["bindings"][0]["members"]

    def update_dataset(dataset, element):
        assert element == ["access_entries"]
        assert dataset.access_entries[0].entity_id == access_entry.entity_id
        assert dataset.access_entries[1].entity_id == EMAIL

    access_entry = bigquery.AccessEntry(
        role="READER",
        entity_type=EntityTypes.USER_BY_EMAIL,
        entity_id="rando",
    )

    _mock_gcloud_bigquery_client(
        monkeypatch,
        [access_entry],
        set_iam_policy,
        update_dataset,
    )

    policy = {
        "bindings": [{"role": GOOGLE_BIGQUERY_USER_ROLE, "members": ["user:rando"]}]
    }
    grant_bigquery_iam_access(policy, [EMAIL])


def test_revoke_upload_access(monkeypatch):
    def set_iam_policy(policy):
        assert any([f"user:rando" in b["members"] for b in policy.bindings])
        print(policy.bindings)
        assert all([f"user:{EMAIL}" not in b["members"] for b in policy.bindings])

    _mock_gcloud_storage_client(
        monkeypatch,
        [
            {"role": GOOGLE_UPLOAD_ROLE, "members": {"user:rando"}},
            {"role": GOOGLE_UPLOAD_ROLE, "members": {f"user:{EMAIL}"}},
        ],
        set_iam_policy,
    )

    revoke_upload_access(EMAIL)


def test_revoke_bigquery_access(monkeypatch):
    def set_iam_policy(resource, body):
        assert resource == "cidc-dfci-staging"
        assert f"user:rando" in body["policy"]["bindings"][0]["members"]

    def update_dataset(dataset, element):
        assert element == ["access_entries"]
        assert dataset.access_entries[0].entity_id == access_entry_1.entity_id

    access_entry_1 = bigquery.AccessEntry(
        role="READER",
        entity_type=EntityTypes.USER_BY_EMAIL,
        entity_id="rando",
    )
    access_entry_2 = bigquery.AccessEntry(
        role="READER",
        entity_type=EntityTypes.USER_BY_EMAIL,
        entity_id=EMAIL,
    )

    _mock_gcloud_bigquery_client(
        monkeypatch,
        [access_entry_1, access_entry_2],
        set_iam_policy,
        update_dataset,
    )

    policy = {
        "bindings": [
            {
                "role": GOOGLE_BIGQUERY_USER_ROLE,
                "members": ["user:rando", f"user:{EMAIL}"],
            }
        ]
    }
    revoke_bigquery_iam_access(policy, EMAIL)


def test_create_intake_bucket(monkeypatch):
    policy = Policy()
    bucket = MagicMock()
    bucket.exists.return_value = False
    bucket.get_iam_policy.return_value = policy
    storage_client = MagicMock()
    storage_client.bucket.return_value = bucket
    storage_client.create_bucket.return_value = bucket

    monkeypatch.setattr(
        "cidc_api.shared.gcloud_client._get_storage_client", lambda: storage_client
    )

    def set_iam_policy(policy):
        assert len(policy.bindings) == 3, str(policy.bindings)
        assert policy.bindings[0]["role"] == GOOGLE_LISTER_ROLE
        assert policy.bindings[0]["members"] == {f"user:rando"}
        assert policy.bindings[1]["role"] == GOOGLE_LISTER_ROLE
        assert policy.bindings[1]["members"] == {f"user:{EMAIL}"}
        assert policy.bindings[2]["role"] == GOOGLE_INTAKE_ROLE
        assert policy.bindings[2]["members"] == {f"user:{EMAIL}"}

    create_intake_bucket(EMAIL)
    _mock_gcloud_storage_client(
        monkeypatch,
        [
            {"role": GOOGLE_LISTER_ROLE, "members": {"user:rando"}},
            {"role": GOOGLE_LISTER_ROLE, "members": {f"user:{EMAIL}"}},
        ],
        set_iam_policy,
    )

    # Bucket name should have structure:
    # <intake bucket prefix>-<10 character email hash>
    name, hash = storage_client.bucket.call_args[0][0].rsplit("-", 1)
    assert name == GOOGLE_INTAKE_BUCKET
    assert len(hash) == 10 and EMAIL not in hash

    # The bucket gets created and permissions get granted
    storage_client.create_bucket.assert_called_once_with(bucket)
    bucket.get_iam_policy.assert_called_once()
    bucket.set_iam_policy.assert_called_once_with(policy)

    # If the bucket already exists, it doesn't get re-created
    storage_client.create_bucket.reset_mock()
    bucket.exists.return_value = True
    create_intake_bucket(EMAIL)
    storage_client.create_bucket.assert_not_called()


def test_refresh_intake_access(monkeypatch):
    _mock_gcloud_storage_client(
        monkeypatch,
        _build_storage_iam_binding(GOOGLE_INTAKE_BUCKET, GOOGLE_INTAKE_ROLE, EMAIL),
        lambda i: i,
    )

    grant_storage_iam_access = MagicMock()
    monkeypatch.setattr(
        "cidc_api.shared.gcloud_client.grant_storage_iam_access",
        grant_storage_iam_access,
    )

    refresh_intake_access(EMAIL)
    args, kwargs = grant_storage_iam_access.call_args_list[0]
    assert args[0].name.startswith(GOOGLE_INTAKE_BUCKET)
    assert args[1:] == (GOOGLE_INTAKE_ROLE, EMAIL)


def test_revoke_intake_access(monkeypatch):
    _mock_gcloud_storage_client(
        monkeypatch,
        _build_storage_iam_binding(GOOGLE_INTAKE_BUCKET, GOOGLE_INTAKE_ROLE, EMAIL),
        lambda i: i,
    )

    revoke_storage_iam_access = MagicMock()
    monkeypatch.setattr(
        "cidc_api.shared.gcloud_client.revoke_storage_iam_access",
        revoke_storage_iam_access,
    )

    revoke_intake_access(EMAIL)
    args, _ = revoke_storage_iam_access.call_args_list[0]
    assert args[0].name.startswith(GOOGLE_INTAKE_BUCKET)
    assert args[1:] == (GOOGLE_INTAKE_ROLE, EMAIL)


def test_grant_download_access_by_names(monkeypatch):
    """
    Check that get_blob_name returns the name of the blob to have the correct input
    Check that grant_download_access_to_blob_names makes ACL calls as expected
    """
    client = _mock_gcloud_storage_client(monkeypatch)

    _get_bucket = MagicMock()
    _get_bucket.return_value = bucket = MagicMock()
    bucket.get_blob.return_value = client.blobs[0]
    monkeypatch.setattr("cidc_api.shared.gcloud_client._get_bucket", _get_bucket)

    blob_names = get_blob_names("10021", "wes_analysis")
    assert blob_names == set([client.blobs[0].name])

    grant_download_access_to_blob_names([EMAIL], blob_name_list=blob_names)
    client.blobs[0].acl.user.assert_called_once_with(EMAIL)
    client.blob_users[0].grant_read.assert_called_once()
    client.blobs[0].acl.save.assert_called_once()
    client.blobs[1].acl.user.assert_not_called()
    client.blobs[1].acl.save.assert_not_called()


def test_grant_download_access(monkeypatch):
    """Check that grant_download_access publishes to ACL grant/revoke download permissions topic"""
    client = _mock_gcloud_storage_client(monkeypatch)
    grant_download_access(EMAIL, "10021", "wes_analysis")

    client.encode_and_publish.assert_called_once()
    args, _ = client.encode_and_publish.call_args
    assert args[0] == str(
        {
            "trial_id": "10021",
            "upload_type": "wes_analysis",
            "user_email_list": [EMAIL],
            "revoke": False,
        }
    )
    assert args[1] == GOOGLE_GRANT_DOWNLOAD_PERMISSIONS_TOPIC


def test_revoke_download_access_from_names(monkeypatch):
    """
    Check that get_blob_name returns the name of the blob to have the correct input
    Check that grant_download_access_to_blob_names makes ACL calls as expected
    """
    client = _mock_gcloud_storage_client(monkeypatch)

    _get_bucket = MagicMock()
    _get_bucket.return_value = bucket = MagicMock()
    bucket.get_blob.return_value = client.blobs[0]
    monkeypatch.setattr(gcloud_client, "_get_bucket", _get_bucket)

    blob_name_list = get_blob_names("10021", "wes_analysis")
    assert blob_name_list == set([client.blobs[0].name])

    revoke_download_access_from_blob_names([EMAIL], blob_name_list=blob_name_list)
    client.blobs[0].acl.user.assert_called_once_with(EMAIL)
    client.blob_users[0].revoke_owner.assert_called_once()
    client.blob_users[0].revoke_write.assert_called_once()
    client.blob_users[0].revoke_read.assert_called_once()
    client.blobs[0].acl.save.assert_called_once()
    client.blobs[1].acl.user.assert_not_called()
    client.blobs[1].acl.save.assert_not_called()


def test_revoke_download_access(monkeypatch):
    """Check that revoke_download_access publishes to ACL grant/revoke download permissions topic"""
    client = _mock_gcloud_storage_client(monkeypatch)
    revoke_download_access(EMAIL, "10021", "wes_analysis")

    client.encode_and_publish.assert_called_once()
    args, _ = client.encode_and_publish.call_args
    assert args[0] == str(
        {
            "trial_id": "10021",
            "upload_type": "wes_analysis",
            "user_email_list": [EMAIL],
            "revoke": True,
        }
    )
    assert args[1] == GOOGLE_GRANT_DOWNLOAD_PERMISSIONS_TOPIC


def test_revoke_all_download_access(monkeypatch):
    """Check that revoke_all_download_access publishes to ACL grant/revoke download permissions topic"""
    client = _mock_gcloud_storage_client(monkeypatch)
    revoke_all_download_access(EMAIL)

    args, _ = client.encode_and_publish.call_args
    assert args[0] == str(
        {
            "trial_id": None,
            "upload_type": None,
            "user_email_list": [EMAIL],
            "revoke": True,
        }
    )
    assert args[1] == GOOGLE_GRANT_DOWNLOAD_PERMISSIONS_TOPIC


def test_xlsx_gcs_uri_format(monkeypatch):

    trial = "whatever"
    template_type = "also_whatever"
    assay_type = "something_else"

    uri = _xlsx_gcs_uri_format.format(
        trial_id=trial,
        template_category=template_type,
        template_type=assay_type,
        upload_moment=datetime.now().isoformat(),
    )
    assert trial in uri
    assert template_type in uri
    assert assay_type in uri


def test_upload_xlsx_to_gcs(monkeypatch):
    trial_id = "test-trial"
    upload_category = "assays"
    upload_type = "olink"
    upload_moment = datetime.now()
    open_file = BytesIO(b"foobar")
    expected_name = (
        f"{trial_id}/xlsx/{upload_category}/{upload_type}/{upload_moment}.xlsx"
    )

    # upload_xlsx_to_gcs should return a `_pseudo_blob` when ENV = "dev"
    res = upload_xlsx_to_gcs(
        trial_id, upload_category, upload_type, open_file, upload_moment
    )
    assert type(res) == _pseudo_blob
    assert res.name == expected_name
    assert res.time_created == upload_moment

    # upload_xlsx_to_gcs should call GCS api when ENV = "prod"
    monkeypatch.setattr(gcloud_client, "ENV", "prod")
    _get_bucket = MagicMock()
    _get_bucket.return_value = bucket = MagicMock()
    bucket.blob.return_value = blob = MagicMock()
    bucket.copy_blob.return_value = copied_blob = MagicMock()
    monkeypatch.setattr("cidc_api.shared.gcloud_client._get_bucket", _get_bucket)
    res = upload_xlsx_to_gcs(
        trial_id, upload_category, upload_type, open_file, upload_moment
    )
    assert res == copied_blob
    assert call(GOOGLE_UPLOAD_BUCKET) in _get_bucket.call_args_list
    assert call(GOOGLE_ACL_DATA_BUCKET) in _get_bucket.call_args_list
    bucket.blob.assert_called_once_with(expected_name)
    blob.upload_from_file.assert_called_once_with(open_file)
    bucket.copy_blob.assert_called_once_with(blob, bucket)


def test_upload_xlsx_to_intake_bucket(monkeypatch):
    trial_id = "test-trial"
    assay_type = "wes"
    xlsx = FileStorage(filename="metadata.xlsx")

    _get_bucket = MagicMock()
    _get_bucket.return_value = bucket = MagicMock()
    bucket.blob.return_value = blob = MagicMock()
    monkeypatch.setattr("cidc_api.shared.gcloud_client._get_bucket", _get_bucket)

    url = upload_xlsx_to_intake_bucket(EMAIL, trial_id, assay_type, xlsx)
    blob.upload_from_file.assert_called_once()
    assert url.startswith(
        "https://console.cloud.google.com/storage/browser/_details/cidc-intake-staging-"
    )
    assert f"/{trial_id}/{assay_type}" in url
    assert url.endswith(".xlsx")


def test_get_signed_url(monkeypatch):
    storage_client = MagicMock()
    storage_client.get_bucket.return_value = bucket = MagicMock()
    bucket.blob.return_value = blob = MagicMock()
    blob.generate_signed_url = lambda **kwargs: kwargs["response_disposition"]

    monkeypatch.setattr(
        "cidc_api.shared.gcloud_client._get_storage_client", lambda: storage_client
    )

    object_name = "path/to/obj"
    signed_url = gcloud_client.get_signed_url(object_name)
    assert signed_url == 'attachment; filename="path_to_obj"'


def test_encode_and_publish(monkeypatch):
    pubsub = MagicMock()
    pubsub.PublisherClient.return_value = pubsub_client = MagicMock()
    pubsub_client.topic_path = lambda proj, top: top
    pubsub_client.publish.return_value = report = MagicMock()
    monkeypatch.setattr(gcloud_client, "pubsub", pubsub)

    # Make sure the ENV = "prod" case publishes
    monkeypatch.setattr(gcloud_client, "ENV", "prod")
    topic = "some-topic"
    content = "some message"
    res = gcloud_client._encode_and_publish(content, topic)
    assert res == report
    pubsub_client.publish.assert_called_once_with(topic, data=bytes(content, "utf-8"))


def mock_encode_and_publish(monkeypatch):
    _encode_and_publish = MagicMock()
    monkeypatch.setattr(
        "cidc_api.shared.gcloud_client._encode_and_publish", _encode_and_publish
    )
    return _encode_and_publish


def test_publish_upload_success(monkeypatch):
    _encode_and_publish = mock_encode_and_publish(monkeypatch)
    gcloud_client.publish_upload_success("foo")
    _encode_and_publish.assert_called_with("foo", settings.GOOGLE_UPLOAD_TOPIC)


def test_publish_patient_sample_update(monkeypatch):
    _encode_and_publish = mock_encode_and_publish(monkeypatch)
    gcloud_client.publish_patient_sample_update("foo")
    _encode_and_publish.assert_called_with("foo", settings.GOOGLE_PATIENT_SAMPLE_TOPIC)


def test_publish_artifact_upload(monkeypatch):
    _encode_and_publish = mock_encode_and_publish(monkeypatch)
    gcloud_client.publish_artifact_upload("foo")
    _encode_and_publish.assert_called_with("foo", settings.GOOGLE_ARTIFACT_UPLOAD_TOPIC)


def test_send_email(monkeypatch):
    _encode_and_publish = mock_encode_and_publish(monkeypatch)

    to_emails = ["test@example.com"]
    subject = "test subject"
    html_content = "<div>test html<div>"
    kwargs = {"kwarg1": "foo", "kwarg2": "bar"}
    expected_json = json.dumps(
        {
            "to_emails": to_emails,
            "subject": subject,
            "html_content": html_content,
            **kwargs,
        }
    )

    # If ENV = "dev", no emails are sent
    gcloud_client.send_email(to_emails, subject, html_content, **kwargs)
    _encode_and_publish.assert_not_called()

    # Check ENV = "prod" behavior
    monkeypatch.setattr(gcloud_client, "ENV", "prod")
    monkeypatch.setattr(gcloud_client, "TESTING", False)
    gcloud_client.send_email(to_emails, subject, html_content, **kwargs)
    _encode_and_publish.assert_called_with(expected_json, settings.GOOGLE_EMAILS_TOPIC)
