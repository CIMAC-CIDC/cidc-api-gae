"""Smoke tests ranging across the CIDC REST API.

This file doesn't contain tests for methods that don't directly correspond
to data resources, like those implemented in the services module (e.g., for
handling upload-related functionality).
"""

from datetime import datetime

from flask import _request_ctx_stack

import pytest
from cidc_api.models import (
    Users,
    DownloadableFiles,
    Permissions,
    TrialMetadata,
    UploadJobs,
    UploadJobStatus,
    CIDCRole,
)

TEST_RECORD_ID = 1
new_user = {"email": "test-admin@email.com"}
user = {
    **new_user,
    "id": TEST_RECORD_ID,
    "role": CIDCRole.ADMIN.value,
    "approval_date": datetime.now(),
}
trial_metadata = {"id": TEST_RECORD_ID, "trial_id": "foo", "metadata_json": {}}
downloadable_file = {
    "id": TEST_RECORD_ID,
    "trial_id": trial_metadata["trial_id"],
    "file_name": "",
    "upload_type": "olink",
    "data_format": "",
    "object_url": "",
    "uploaded_timestamp": datetime.now(),
    "file_size_bytes": 1,
}
permission = {
    "id": TEST_RECORD_ID,
    "granted_to_user": TEST_RECORD_ID,
    "trial_id": trial_metadata["trial_id"],
    "upload_type": downloadable_file["upload_type"],
}
upload_job = {
    "id": TEST_RECORD_ID,
    "trial_id": trial_metadata["trial_id"],
    "uploader_email": user["email"],
    "upload_type": downloadable_file["upload_type"],
    "metadata_patch": {},
    "gcs_xlsx_uri": "",
    "multifile": False,
    "status": UploadJobStatus.STARTED.value,
}


@pytest.fixture
def app_with_admin_user(app, monkeypatch):
    def fake_auth(*args):
        _request_ctx_stack.top.current_user = Users(**user)
        return True

    monkeypatch.setattr(app.auth, "authorized", fake_auth)

    return app


ETAG = "test-etag"


@pytest.fixture
def db_with_records(db):
    extra = {"_etag": ETAG}
    db.add(Users(**user, **extra))
    db.add(TrialMetadata(**trial_metadata, **extra))
    db.commit()

    db.add(DownloadableFiles(**downloadable_file, **extra))
    db.add(Permissions(**permission, **extra))
    db.add(UploadJobs(**upload_job, **extra))
    db.commit()

    return db


print(CIDCRole.CIMAC_USER.value)

resource_requests = {
    "new_users": {"json": new_user, "model": Users, "allowed_methods": {"POST"}},
    "users": {
        "json": user,
        "model": Users,
        "allowed_methods": {"POST", "PATCH", "GET"},
        "update": {"role": CIDCRole.CIMAC_USER.value},
        "filters": {
            "empty": {
                "where": f"role=='{CIDCRole.CIMAC_USER.value}' and email=='{user['email']}'"
            },
            "full": {
                "where": f"role=='{CIDCRole.CIMAC_USER.value}' or email=='{user['email']}'"
            },
        },
        "additional_records": [
            {**user, "id": 2, "email": "foo@bar.com"},
            {**user, "id": 3, "email": "fizz@buzz.com"},
        ],
    },
    "trial_metadata": {
        "json": trial_metadata,
        "model": TrialMetadata,
        "allowed_methods": {"POST", "PATCH", "GET"},
        "lookup_field": "trial_id",
        "update": {"metadata_json": {"foo": "bar"}},
    },
    "downloadable_files": {
        "json": downloadable_file,
        "model": DownloadableFiles,
        "allowed_methods": {"GET"},
        "setup": ["trial_metadata"],
        "update": {"upload_type": "fizzbuzz"},
        "filters": {
            "empty": {
                "where": f"trial_id=='{trial_metadata['trial_id']}' and upload_type=='wes'"
            },
            "full": {
                "where": f"trial_id=='{trial_metadata['trial_id']}' and upload_type=='olink'"
            },
        },
        "additional_records": [
            {**downloadable_file, "id": 2, "object_url": "foo/bar"},
            {**downloadable_file, "id": 3, "object_url": "fizz/buzz"},
        ],
    },
    "permissions": {
        "json": permission,
        "model": Permissions,
        "allowed_methods": {"POST", "PATCH", "GET", "DELETE"},
        "setup": ["users", "trial_metadata"],
        "update": {"upload_type": "fizzbuzz"},
        "filters": {
            "empty": {"where": "granted_to_user==2"},
            "full": {"where": "granted_to_user==1"},
        },
    },
    "upload_jobs": {
        "json": upload_job,
        "model": UploadJobs,
        "allowed_methods": {"PATCH", "GET"},
        "setup": ["users", "trial_metadata"],
        "update": {"upload_type": "fizzbuzz"},
    },
}


def assert_dict_contains(base, target):
    assert isinstance(target, dict) and isinstance(base, dict)
    for key, value in target.items():
        assert key in base
        assert base[key] == value or isinstance(value, datetime)


@pytest.mark.parametrize("resource, config", resource_requests.items())
def test_resource_post(resource, config, app_with_admin_user, db):
    """Test resource creation via POST."""
    client = app_with_admin_user.test_client()

    if "setup" in config:
        for setup_resource in config["setup"]:
            client.post(setup_resource, json=resource_requests[setup_resource]["json"])

    # Try to create the item with POST
    response = client.post(resource, json=config["json"])
    if "POST" in config["allowed_methods"]:
        assert response.status_code == 201
        # Make sure it was created
        item = db.query(config["model"]).one().__dict__
        assert_dict_contains(item, config["json"])
    else:
        assert response.status_code == 405


@pytest.mark.parametrize("resource, config", resource_requests.items())
def test_resource_and_item_get(resource, config, app_with_admin_user, db_with_records):
    client = app_with_admin_user.test_client()

    # resource-level GET
    response = client.get(resource)
    if "GET" in config["allowed_methods"]:
        assert response.status_code == 200
        item = response.json["_items"][0]
        assert_dict_contains(item, config["json"])
        if config.get("pagination"):
            assert response.json["_meta"]["total"] == 3
        else:
            assert response.json["_meta"]["total"] == 1
    else:
        assert response.status_code == 405

    # item-level GET
    lookup = config["json"].get(config.get("lookup_field") or "id")
    response = client.get(f"{resource}/{lookup}")
    if "GET" in config["allowed_methods"]:
        assert response.status_code == 200
        assert_dict_contains(response.json, config["json"])
    else:
        assert response.status_code in (404, 405)


@pytest.mark.parametrize("resource, config", resource_requests.items())
def test_item_patch(resource, config, app_with_admin_user, db_with_records):
    client = app_with_admin_user.test_client()

    # Try to update the resource
    lookup = config["json"].get(config.get("lookup_field") or "id")
    response = client.patch(f"{resource}/{lookup}", json=config.get("update"))
    if "PATCH" in config["allowed_methods"]:
        # Need to match etag
        assert response.status_code == 428
        response = client.patch(
            f"{resource}/{lookup}",
            json=config.get("update"),
            headers={"if-match": ETAG},
        )
        assert response.status_code == 200
        # Check that the record was updated
        item = db_with_records.query(config["model"]).one().__dict__
        assert_dict_contains(item, config["update"])
    else:
        assert response.status_code in (404, 405)


@pytest.mark.parametrize("resource, config", resource_requests.items())
def test_item_put(resource, config, app_with_admin_user, db_with_records):
    client = app_with_admin_user.test_client()

    # Try to PUT the resource - this is disallowed for all resources.
    lookup = config["json"].get(config.get("lookup_field") or "id")
    response = client.put(f"{resource}/{lookup}", json=config["json"])
    if "PUT" in config["allowed_methods"]:
        assert response.status_code == 200
        assert response.json == config["json"]
    else:
        assert response.status_code in (404, 405)


@pytest.mark.parametrize("resource, config", resource_requests.items())
def test_item_delete(resource, config, app_with_admin_user, db_with_records):
    client = app_with_admin_user.test_client()

    # Try to DELETE the resource - this is disallowed for all resources.
    lookup = config["json"].get(config.get("lookup_field") or "id")
    response = client.delete(f"{resource}/{lookup}", headers={"if-match": ETAG})
    if "DELETE" in config["allowed_methods"]:
        assert response.status_code == 204
    else:
        assert response.status_code in (404, 405)


@pytest.mark.parametrize("resource, config", resource_requests.items())
def test_resource_filters(resource, config, app_with_admin_user, db_with_records):
    if "filters" not in config:
        return

    client = app_with_admin_user.test_client()

    full_response = client.get(resource, query_string=config["filters"]["full"])
    assert full_response.status_code == 200
    item = full_response.json["_items"][0]
    assert_dict_contains(item, config["json"])

    empty_response = client.get(resource, query_string=config["filters"]["empty"])
    assert empty_response.status_code == 200
    assert empty_response.json["_items"] == []


@pytest.mark.parametrize("resource, config", resource_requests.items())
def test_resource_pagination(resource, config, app_with_admin_user, db_with_records):
    if "additional_records" not in config:
        return

    # Insert additional records for pagination testing
    for record in config["additional_records"]:
        db_with_records.add(config["model"](**record))
    db_with_records.commit()

    client = app_with_admin_user.test_client()

    # Check that max_results = 1 returns only one result
    response = client.get(resource, query_string={"max_results": 1})
    assert response.status_code == 200
    assert len(response.json["_items"]) == 1
    assert response.json["_items"][0]["id"] == 1

    # Check that changing the sorting seems to work
    response = client.get(
        resource, query_string={"max_results": 1, "sort": "[('id', -1)]"}
    )
    assert response.status_code == 200
    assert response.json["_items"][0]["id"] == 3

    # Check that pagination seems to work
    page_1_response = client.get(resource, query_string={"max_results": 2, "page": 1})
    assert page_1_response.status_code == 200
    assert len(page_1_response.json["_items"]) == 2
    page_2_response = client.get(resource, query_string={"max_results": 2, "page": 2})
    assert page_2_response.status_code == 200
    assert len(page_2_response.json["_items"]) == 1


def test_endpoint_urls(app):
    """
    Ensure that the API has exactly the endpoints we expect.
    """
    expected_endpoints = {
        "/",
        "/downloadable_files",
        "/downloadable_files/download_url",
        "/downloadable_files/filter_facets",
        '/downloadable_files/<regex("[0-9]+"):id>',
        "/info/assays",
        "/info/analyses",
        "/info/manifests",
        "/info/extra_data_types",
        "/info/templates/<template_family>/<template_type>",
        "/ingestion/validate",
        "/ingestion/upload_manifest",
        "/ingestion/upload_assay",
        "/ingestion/upload_analysis",
        "/ingestion/extra-assay-metadata",
        "/ingestion/poll_upload_merge_status",
        "/permissions",
        '/permissions/<regex("[0-9]+"):id>',
        "/trial_metadata",
        '/trial_metadata/<regex("[a-zA-Z0-9_-]+"):trial_id>',
        "/upload_jobs",
        '/upload_jobs/<regex("[0-9]+"):id>',
        "/users",
        "/users/self",
        '/users/<regex("[0-9]+"):id>',
        "/new_users",
    }

    # Check that every endpoint included in the API is expected.
    endpoints = set([rule.rule for rule in app.url_map._rules])
    assert endpoints == expected_endpoints
