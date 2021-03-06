from datetime import datetime
from typing import Tuple

from cidc_api.resources.trial_metadata import trial_modifier_roles
from cidc_api.models import (
    Users,
    TrialMetadata,
    TrialMetadataSchema,
    Permissions,
    CIDCRole,
    DownloadableFiles,
)

from ..utils import mock_current_user, make_role, mock_gcloud_client


def setup_user(cidc_api, monkeypatch) -> int:
    current_user = Users(
        email="test@email.com",
        role=CIDCRole.CIMAC_USER.value,
        approval_date=datetime.now(),
    )
    mock_current_user(current_user, monkeypatch)

    with cidc_api.app_context():
        current_user.insert()
        return current_user.id


def setup_trial_metadata(cidc_api, user_id=None) -> Tuple[int, int]:
    """Insert two trials into the database and return their IDs."""

    def create_trial(n, grant_perm=False):
        trial_id = f"test-trial-{n}"
        metadata_json = {
            "protocol_identifier": trial_id,
            "participants": [],
            "allowed_collection_event_names": [],
            "allowed_cohort_names": [],
        }
        trial = TrialMetadata(trial_id=trial_id, metadata_json=metadata_json)
        trial.insert()
        if grant_perm and user_id:
            Permissions(
                granted_to_user=user_id,
                trial_id=trial.trial_id,
                upload_type="wes",
                granted_by_user=user_id,
            ).insert()
            Permissions(
                granted_to_user=user_id,
                trial_id=trial.trial_id,
                upload_type="cytof",
                granted_by_user=user_id,
            ).insert()
        return trial.id

    with cidc_api.app_context():
        return create_trial(1, grant_perm=True), create_trial(2)


def test_list_trials(cidc_api, clean_db, monkeypatch):
    """Check that listing trials works as expected"""
    mock_gcloud_client(monkeypatch)
    user_id = setup_user(cidc_api, monkeypatch)
    trial_1, trial_2 = setup_trial_metadata(cidc_api, user_id)

    client = cidc_api.test_client()

    # A CIMAC user can list trials that they're allowed to see
    res = client.get("/trial_metadata")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 1
    assert res.json["_items"][0]["id"] == trial_1
    assert "file_bundle" not in res.json["_items"][0]

    # Allowed users can get all trials
    for role in trial_modifier_roles:
        make_role(user_id, role, cidc_api)

        res = client.get("/trial_metadata")
        assert res.status_code == 200
        assert len(res.json["_items"]) == 2
        assert res.json["_meta"]["total"] == 2
        assert set([t["id"] for t in res.json["_items"]]) == set([trial_1, trial_2])
        assert not any("file_bundle" in t for t in res.json["_items"])

    # Listing trials with file bundles excludes trials with no files
    res = client.get("/trial_metadata?include_file_bundles=true")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 0

    # Add some files...
    with cidc_api.app_context():
        # for trial 1
        for id, (type, facet_group) in enumerate(
            [
                ("cytof", "/cytof/spike_in.fcs"),
                ("cytof", "/cytof/source_.fcs"),
                ("cytof", "/cytof_analysis/profiling.csv"),
                ("wes", "/wes/r1_.fastq.gz"),
            ]
        ):
            DownloadableFiles(
                id=id,
                trial_id="test-trial-1",
                facet_group=facet_group,
                object_url=f"test-trial-1/{facet_group}",
                file_name="",
                data_format="",
                upload_type=type,
                file_size_bytes=0,
                uploaded_timestamp=datetime.now(),
            ).insert()
        # for trial 2
        for id_minus_4, (type, facet_group) in enumerate(
            [
                ("participants info", "csv|participants info"),
                ("mif", "/mif/roi_/phenotype_map.tif"),
            ]
        ):
            DownloadableFiles(
                id=id_minus_4 + 4,
                trial_id="test-trial-2",
                facet_group=facet_group,
                object_url=f"test-trial-2/{facet_group}",
                file_name="",
                data_format="",
                upload_type=type,
                file_size_bytes=0,
                uploaded_timestamp=datetime.now(),
            ).insert()

    # Listing trials with populated file bundles (also, check that sorting works)
    res = client.get(
        "/trial_metadata?include_file_bundles=true&sort_field=trial_id&sort_direction=asc"
    )
    assert res.status_code == 200
    assert len(res.json["_items"]) == 2
    assert res.json["_items"][0]
    [trial_json_1, trial_json_2] = res.json["_items"]
    assert set(trial_json_1["file_bundle"]["CyTOF"]["source"]) == set([0, 1])
    assert trial_json_1["file_bundle"]["CyTOF"]["analysis"] == [2]
    assert trial_json_1["file_bundle"]["WES"]["source"] == [3]
    assert trial_json_2["file_bundle"]["Participants Info"]["clinical"] == [4]
    assert trial_json_2["file_bundle"]["mIF"]["analysis"] == [5]

    # Filtering by trial id seems to work when file bundles are included
    res = client.get("/trial_metadata?include_file_bundles=true&trial_ids=test-trial-1")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 1
    assert res.json["_items"][0]["trial_id"] == "test-trial-1"

    # Pagination seems to work when file bundles are included
    res = client.get("/trial_metadata?include_file_bundles=true&page_size=1")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 1


def test_get_trial(cidc_api, clean_db, monkeypatch):
    """Check that getting a single trial works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    trial_record_id, _ = set(setup_trial_metadata(cidc_api))
    with cidc_api.app_context():
        trial = TrialMetadata.find_by_id(trial_record_id)

    client = cidc_api.test_client()

    # Non-admins can't get single trials
    res = client.get(f"/trial_metadata/{trial.trial_id}")
    assert res.status_code == 401

    # Allowed users can get single trials
    for role in trial_modifier_roles:
        make_role(user_id, role, cidc_api)
        res = client.get(f"/trial_metadata/{trial.trial_id}")
        assert res.status_code == 200
        assert res.json == TrialMetadataSchema().dump(trial)

        # Getting non-existent trials yields 404
        res = client.get(f"/trial_metadata/123212321")
        assert res.status_code == 404


def test_get_trial_by_trial_id(cidc_api, clean_db, monkeypatch):
    """Check that getting a single trial by trial id works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    trial_id, _ = set(setup_trial_metadata(cidc_api))
    with cidc_api.app_context():
        trial = TrialMetadata.find_by_id(trial_id)

    client = cidc_api.test_client()

    # Non-admins can't get single trials
    res = client.get(f"/trial_metadata/{trial.trial_id}")
    assert res.status_code == 401

    # Allowed users can get single trials
    for role in trial_modifier_roles:
        make_role(user_id, role, cidc_api)
        res = client.get(f"/trial_metadata/{trial.trial_id}")
        assert res.status_code == 200
        assert res.json == TrialMetadataSchema().dump(trial)

        # Getting non-existent trials yields 404
        res = client.get(f"/trial_metadata/foobar")
        assert res.status_code == 404


bad_trial_json = {"trial_id": "foo", "metadata_json": {"foo": "bar"}}
bad_trial_error_message = {
    "errors": [
        "'metadata_json': error on [root]={'foo': 'bar'}: Additional properties are not allowed ('foo' was unexpected)",
        "'metadata_json': error on [root]={'foo': 'bar'}: missing required property 'protocol_identifier'",
        "'metadata_json': error on [root]={'foo': 'bar'}: missing required property 'participants'",
        "'metadata_json': error on [root]={'foo': 'bar'}: missing required property 'allowed_cohort_names'",
        "'metadata_json': error on [root]={'foo': 'bar'}: missing required property 'allowed_collection_event_names'",
    ]
}


def test_create_trial(cidc_api, clean_db, monkeypatch):
    """Check that creating a new trial works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    trial_id = "test-trial"
    trial_json = {
        "trial_id": trial_id,
        "metadata_json": {
            "protocol_identifier": trial_id,
            "participants": [],
            "allowed_collection_event_names": [],
            "allowed_cohort_names": [],
        },
    }

    client = cidc_api.test_client()

    # Non-admins can't create trials
    res = client.post("/trial_metadata", json=trial_json)
    assert res.status_code == 401

    # Allowed users can create trials
    for role in trial_modifier_roles:
        make_role(user_id, role, cidc_api)
        res = client.post("/trial_metadata", json=trial_json)
        assert res.status_code == 201
        assert {**res.json, **trial_json} == res.json

        # No two trials can have the same trial_id
        res = client.post("/trial_metadata", json=trial_json)
        assert res.status_code == 400

        # No trial can be created with invalid metadata
        bad_trial_json = {"trial_id": "foo", "metadata_json": {"foo": "bar"}}
        res = client.post("/trial_metadata", json=bad_trial_json)
        assert res.status_code == 422
        assert res.json["_error"]["message"] == bad_trial_error_message

        # Clear created trial
        with cidc_api.app_context():
            trial = TrialMetadata.find_by_trial_id(trial_id)
            trial.delete()


def test_update_trial(cidc_api, clean_db, monkeypatch):
    """Check that updating a trial works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    trial_record_id, _ = set(setup_trial_metadata(cidc_api))
    with cidc_api.app_context():
        trial = TrialMetadata.find_by_id(trial_record_id)

    client = cidc_api.test_client()

    # Non-admins can't update single trials
    res = client.patch(f"/trial_metadata/{trial.trial_id}")
    assert res.status_code == 401

    for role in trial_modifier_roles:
        make_role(user_id, role, cidc_api)

        # A missing ETag blocks an update
        res = client.patch(f"/trial_metadata/{trial.trial_id}")
        assert res.status_code == 428

        # An incorrect ETag blocks an update
        res = client.patch(
            f"/trial_metadata/{trial.trial_id}", headers={"If-Match": "foo"}
        )
        assert res.status_code == 412

        # No trial can be updated to have invalid metadata
        res = client.patch(
            f"/trial_metadata/{trial.trial_id}",
            headers={"If-Match": trial._etag},
            json={"metadata_json": bad_trial_json["metadata_json"]},
        )
        assert res.status_code == 422
        print(res.json["_error"]["message"])
        assert res.json["_error"]["message"] == bad_trial_error_message

        # An admin can successfully update a trial
        new_metadata_json = {
            **trial.metadata_json,
            "allowed_collection_event_names": ["bazz"],
            "allowed_cohort_names": ["buzz"],
        }
        res = client.patch(
            f"/trial_metadata/{trial.trial_id}",
            headers={"If-Match": trial._etag},
            json={"metadata_json": new_metadata_json},
        )
        assert res.status_code == 200
        assert res.json["id"] == trial.id
        assert res.json["trial_id"] == trial.trial_id
        assert res.json["metadata_json"] == new_metadata_json

        with cidc_api.app_context():
            trial = TrialMetadata.find_by_id(trial.id)
