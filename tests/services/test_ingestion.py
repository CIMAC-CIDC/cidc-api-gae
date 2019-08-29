import io
from unittest.mock import MagicMock

import pytest
from werkzeug.exceptions import (
    HTTPException,
    InternalServerError,
    BadRequest,
    NotImplemented,
)

from config.settings import GOOGLE_UPLOAD_BUCKET
from services.ingestion import extract_schema_and_xlsx

from . import open_data_file
from ..util import assert_same_elements
from ..conftest import TEST_EMAIL
from cidc_api.models import TrialMetadata, Users


@pytest.fixture
def pbmc_valid_xlsx():
    with open_data_file("pbmc_valid.xlsx") as xlsx:
        yield xlsx


@pytest.fixture
def pbmc_invalid_xlsx():
    yield open_data_file("pbmc_invalid.xlsx")


@pytest.fixture
def wes_xlsx():
    yield open_data_file("wes_data.xlsx")


@pytest.fixture
def olink_xlsx():
    yield open_data_file("olink_data.xlsx")


def form_data(filename=None, fp=None, schema=None):
    """
    If no filename is provided, return some text form data.
    If a filename is provided but no opened file (`fp`) is provided,
    return form data with a mock file included.
    If a filename and an opened file is provided, return
    form data with the provided file included.
    """
    data = {"foo": "bar"}
    if schema:
        data["schema"] = schema
    if filename:
        fp = fp or io.BytesIO(b"blah blah")
        data["template"] = (fp, filename)
    return data


VALIDATE = "/ingestion/validate"
ASSAY_UPLOAD = "/ingestion/upload_assay"
MANIFEST_UPLOAD = "/ingestion/upload_manifest"


def test_validate_valid_template(app_no_auth, pbmc_valid_xlsx):
    """Ensure that the validation endpoint returns no errors for a known-valid .xlsx file"""
    client = app_no_auth.test_client()
    data = form_data("pbmc.xlsx", pbmc_valid_xlsx, "pbmc")
    res = client.post(VALIDATE, data=data)
    assert res.status_code == 200
    assert res.json["errors"] == []


def test_validate_invalid_template(app_no_auth, pbmc_invalid_xlsx):
    """Ensure that the validation endpoint returns errors for a known-invalid .xlsx file"""
    client = app_no_auth.test_client()
    data = form_data("pbmc.xlsx", pbmc_invalid_xlsx, "pbmc")
    res = client.post(VALIDATE, data=data)
    assert res.status_code == 200
    assert len(res.json["errors"]) > 0


@pytest.mark.parametrize(
    "url,data,error,message",
    [
        # Missing form content
        [VALIDATE, None, BadRequest, "form content"],
        # Form missing template file
        [VALIDATE, form_data(), BadRequest, "template file"],
        # Template file is non-.xlsx
        [VALIDATE, form_data("text.txt"), BadRequest, ".xlsx file"],
        # URL is missing "schema" query param
        [VALIDATE, form_data("text.xlsx"), BadRequest, "form entry for 'schema'"],
        # "schema" query param references non-existent schema
        [
            VALIDATE,
            form_data("test.xlsx", schema="foo/bar"),
            BadRequest,
            "Unknown template type foo/bar",
        ],
    ],
)
def test_extract_schema_and_xlsx_failures(app, url, data, error, message):
    """
    Test that we get the expected errors when trying to extract 
    schema/template from a malformed request.
    """
    with app.test_request_context(url, data=data):
        with pytest.raises(error, match=message):
            extract_schema_and_xlsx()


def test_upload_manifest(app_no_auth, pbmc_valid_xlsx):
    """Ensure the upload_manifest endpoint follows the expected execution flow"""
    client = app_no_auth.test_client()

    res = client.post(
        MANIFEST_UPLOAD, data=form_data("pbmc.xlsx", pbmc_valid_xlsx, "pbmc")
    )
    assert res.status_code == 501  # Not Implemented


def test_upload_wes(app_no_auth, wes_xlsx, test_user, db, monkeypatch):
    """Ensure the upload endpoint follows the expected execution flow"""
    client = app_no_auth.test_client()

    grant_write = MagicMock()
    monkeypatch.setattr("gcloud_client.grant_upload_access", grant_write)

    with app_no_auth.app_context():
        TrialMetadata.create("10021", {})
        Users.create(profile={"email": TEST_EMAIL})
    res = client.post(ASSAY_UPLOAD, data=form_data("wes.xlsx", wes_xlsx, "wes"))
    assert res.json
    assert "url_mapping" in res.json

    url_mapping = res.json["url_mapping"]

    # We expect local_path to map to a gcs object name with gcs_prefix
    # based on the contents of wes_xlsx.
    local_path = "/local/path/to/rgm.1.1.1.txt"
    gcs_prefix = "wes example PA 1/wes example SA 1.1/wes example aliquot 1.1.1/wes/read_group_mapping_file/"
    gcs_object_name = url_mapping[local_path]
    assert local_path in url_mapping
    assert gcs_object_name.startswith(gcs_prefix)
    assert gcs_object_name.endswith(local_path)

    # Check that we tried to grant IAM upload access to gcs_object_name
    grant_write.assert_called_with(GOOGLE_UPLOAD_BUCKET, test_user.email)

    # Track whether we revoke IAM upload access after updating the job status
    revoke_write = MagicMock()
    monkeypatch.setattr("gcloud_client.revoke_upload_access", revoke_write)

    # Track whether we publish an upload success to pub/sub after updating the job status
    publish_success = MagicMock()
    monkeypatch.setattr("gcloud_client.publish_upload_success", publish_success)

    job_id = res.json["job_id"]
    update_url = f"/assay_uploads/{job_id}"

    # Report an upload failure
    res = client.patch(
        update_url,
        json={"status": "errored"},
        headers={"If-Match": res.json["job_etag"]},
    )
    assert res.status_code == 200
    revoke_write.assert_called_with(GOOGLE_UPLOAD_BUCKET, test_user.email)
    # This was an upload failure, so success shouldn't have been published
    publish_success.assert_not_called()

    # Report an upload success
    res = client.patch(
        update_url,
        json={"status": "completed"},
        headers={"If-Match": res.json["_etag"]},
    )
    publish_success.assert_called_with(job_id)


OLINK_TESTDATA = [
    ("/local/path/combined.xlsx", "olink/study_npx/"),
    ("assay1_npx.xlsx", "olink/assay_npx/"),
    ("ct2.xlsx", "olink/assay_raw_ct/"),
]


def test_upload_olink(app_no_auth, olink_xlsx, test_user, db, monkeypatch):
    """Ensure the upload endpoint follows the expected execution flow"""
    client = app_no_auth.test_client()

    grant_write = MagicMock()
    monkeypatch.setattr("gcloud_client.grant_upload_access", grant_write)

    res = client.post(ASSAY_UPLOAD, data=form_data("olink.xlsx", olink_xlsx, "olink"))
    assert res.json
    assert "url_mapping" in res.json

    url_mapping = res.json["url_mapping"]

    # We expect local_path to map to a gcs object name with gcs_prefix
    # based on the contents of olink_xlsx.
    for local_path, gcs_prefix in OLINK_TESTDATA:
        gcs_object_name = url_mapping[local_path]
        assert local_path in url_mapping
        assert gcs_object_name.startswith(gcs_prefix)
        assert gcs_object_name.endswith(local_path)

    # Check that we tried to grant IAM upload access to gcs_object_name
    grant_write.assert_called_with(GOOGLE_UPLOAD_BUCKET, test_user.email)

    # Track whether we revoke IAM upload access after updating the job status
    revoke_write = MagicMock()
    monkeypatch.setattr("gcloud_client.revoke_upload_access", revoke_write)

    # Track whether we publish an upload success to pub/sub after updating the job status
    publish_success = MagicMock()
    monkeypatch.setattr("gcloud_client.publish_upload_success", publish_success)

    job_id = res.json["job_id"]
    update_url = f"/assay_uploads/{job_id}"

    # Report an upload failure
    res = client.patch(
        update_url,
        json={"status": "errored"},
        headers={"If-Match": res.json["job_etag"]},
    )
    assert res.status_code == 200
    revoke_write.assert_called_with(GOOGLE_UPLOAD_BUCKET, test_user.email)
    # This was an upload failure, so success shouldn't have been published
    publish_success.assert_not_called()

    # Report an upload success
    res = client.patch(
        update_url,
        json={"status": "completed"},
        headers={"If-Match": res.json["_etag"]},
    )
    publish_success.assert_called_with(job_id)


def test_signed_upload_urls(app_no_auth, monkeypatch):
    """
    Ensure the signed upload urls endpoint responds with the expected structure
    
    TODO: an integration test that actually calls out to GCS
    """
    client = app_no_auth.test_client()
    data = {
        "directory_name": "my-assay-run-id",
        "object_names": ["my-fastq-1.fastq.gz", "my-fastq-2.fastq.gz"],
    }

    monkeypatch.setattr("google.cloud.storage.Client", MagicMock)
    res = client.post("/ingestion/signed-upload-urls", json=data)

    assert_same_elements(res.json.keys(), data["object_names"])
