import json
from datetime import datetime
from typing import Tuple

from cidc_api.models import (
    Users,
    DownloadableFiles,
    DownloadableFileSchema,
    TrialMetadata,
    Permissions,
    CIDCRole,
)

from ..utils import mock_current_user, make_admin


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


trial_id = "test-trial"
upload_types = ["olink", "cytof"]


def make_file(
    object_url, upload_type, analysis_friendly, tid=trial_id
) -> DownloadableFiles:
    return DownloadableFiles(
        trial_id=tid,
        upload_type=upload_type,
        object_url=object_url,
        data_format="",
        uploaded_timestamp=datetime.now(),
        file_size_bytes=0,
        file_name="",
        analysis_friendly=analysis_friendly,
    )


def make_empty_metadata(trial_id: str) -> dict:
    return {
        "protocol_identifier": trial_id,
        "allowed_collection_event_names": [],
        "allowed_cohort_names": [],
        "participants": [],
    }


def setup_downloadable_files(cidc_api) -> Tuple[int, int]:
    """Insert two downloadable files into the database."""
    trial_id = "test-trial"
    trial = TrialMetadata(
        trial_id=trial_id, metadata_json=make_empty_metadata(trial_id)
    )

    file1, file2 = [
        make_file(f"{trial_id}/{t}/{i}/foo.ext", t, i == 1)
        for i, t in enumerate(upload_types)
    ]

    with cidc_api.app_context():
        trial.insert()
        file1.insert()
        file2.insert()

        return file1.id, file2.id


def setup_faceted_search_files(cidc_api):
    """Insert multiple downloadable files for faceted search testing"""
    tid1 = "t1"
    tid2 = "t2"
    files = [
        make_file(f"{tid1}/tnp/manifest.xlsx", "tumor_normal_pairing", False, tid1),
        make_file(f"{tid1}/wes/source/foo.bam", "wes", False, tid1),
        make_file(f"{tid1}/wes/report/foo.ext", "wes_analysis", True, tid1),
        make_file(f"{tid1}/samples.csv", "samples info", True, tid1),
        make_file(f"{tid1}/participants.csv", "participants info", True, tid1),
        make_file(f"{tid2}/plasma/manifest.xlsx", "plasma", False, tid2),
        make_file(f"{tid2}/cytof/source/source.fcs", "cytof", False, tid2),
        make_file(f"{tid2}/cytof/cell_counts/counts.csv", "cytof_analysis", True, tid2),
        make_file(f"{tid2}/samples.csv", "samples info", True, tid2),
        make_file(f"{tid2}/participants.csv", "participants info", True, tid2),
    ]
    with cidc_api.app_context():
        TrialMetadata(trial_id=tid1, metadata_json=make_empty_metadata(tid1)).insert()
        TrialMetadata(trial_id=tid2, metadata_json=make_empty_metadata(tid2)).insert()
        for file in files:
            file.insert()


# Possible facets we expect for data added by `setup_faceted_search_files`
expected_facets = {
    "assay_types": {"cytof": ["cell_counts", "source"], "wes": ["report"]},
    "clinical_types": ["participants info", "samples info"],
    "sample_types": ["plasma", "tumor_normal_pairing"],
    "trial_ids": ["t2", "t1"],
}


def test_list_downloadable_files(cidc_api, clean_db, monkeypatch):
    """Check that getting a list of files works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    file_id_1, file_id_2 = setup_downloadable_files(cidc_api)

    client = cidc_api.test_client()

    # Non-admins can't get files they don't have permissions for
    res = client.get("/downloadable_files")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 0
    assert res.json["_meta"]["total"] == 0

    # Give the user one permission
    with cidc_api.app_context():
        perm = Permissions(
            granted_to_user=user_id, trial_id=trial_id, upload_type=upload_types[0]
        )
        perm.insert()

    # Non-admins can view files for which they have permission
    res = client.get("/downloadable_files")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 1
    assert res.json["_meta"]["total"] == 1
    assert res.json["_items"][0]["id"] == file_id_1

    simple_query = {"assay_types": json.dumps({"cytof": ["1"]})}

    # Non-admin filter queries exclude files they aren't allowed to view
    res = client.get("/downloadable_files", query_string=simple_query)
    assert res.status_code == 200
    assert len(res.json["_items"]) == 0
    assert res.json["_meta"]["total"] == 0

    # Admins can view all files regardless of permissions
    make_admin(user_id, cidc_api)
    res = client.get("/downloadable_files")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 2
    assert res.json["_meta"]["total"] == 2
    assert set([f["id"] for f in res.json["_items"]]) == set([file_id_1, file_id_2])

    # Admin filter queries include any files that fit the criteria
    res = client.get("/downloadable_files", query_string=simple_query)
    assert res.status_code == 200
    assert len(res.json["_items"]) == 1
    assert res.json["_meta"]["total"] == 1
    assert res.json["_items"][0]["id"] == file_id_2

    # Test a more complex query
    setup_faceted_search_files(cidc_api)
    res = client.get(
        "/downloadable_files",
        query_string={
            "trial_ids": json.dumps(["t2", trial_id]),
            "assay_types": json.dumps(
                {"cytof": ["source", "cell_counts"], "olink": ["0"]}
            ),
            "clinical_types": json.dumps(["samples info"]),
        },
    )
    assert res.status_code == 200
    assert len(res.json["_items"]) == 4
    assert sorted(["cytof", "cytof_analysis", "olink", "samples info"]) == sorted(
        [f["upload_type"] for f in res.json["_items"]]
    )


def test_get_downloadable_file(cidc_api, clean_db, monkeypatch):
    """Check that getting a single file works as expected."""
    user_id = setup_user(cidc_api, monkeypatch)
    file_id_1, file_id_2 = setup_downloadable_files(cidc_api)

    client = cidc_api.test_client()

    # Non-admins get 404s for single files they don't have permision to view
    res = client.get(f"/downloadable_files/{file_id_1}")
    assert res.status_code == 404

    # Give the user one permission
    with cidc_api.app_context():
        perm = Permissions(
            granted_to_user=user_id, trial_id=trial_id, upload_type=upload_types[0]
        )
        perm.insert()

    # Non-admins can get single files that they have permision to view
    res = client.get(f"/downloadable_files/{file_id_1}")
    assert res.status_code == 200
    assert res.json["id"] == file_id_1

    # Admins can get any file regardless of permissions
    make_admin(user_id, cidc_api)
    res = client.get(f"/downloadable_files/{file_id_2}")
    assert res.status_code == 200
    assert res.json["id"] == file_id_2

    # Non-existent files yield 404
    res = client.get(f"/downloadable_files/123212321")
    assert res.status_code == 404


def test_get_filter_facets(cidc_api, clean_db, monkeypatch):
    """Check that getting filter facets works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    setup_faceted_search_files(cidc_api)

    client = cidc_api.test_client()

    res = client.get("/downloadable_files/filter_facets")
    assert res.status_code == 200
    for array_field in ["clinical_types", "sample_types", "trial_ids"]:
        assert sorted(res.json[array_field]) == sorted(expected_facets[array_field])
    assert sorted(res.json["assay_types"]["cytof"]) == sorted(
        expected_facets["assay_types"]["cytof"]
    )
    assert sorted(res.json["assay_types"]["wes"]) == sorted(
        expected_facets["assay_types"]["wes"]
    )


def test_get_download_url(cidc_api, clean_db, monkeypatch):
    """Check that generating a GCS signed URL works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    file_id, _ = setup_downloadable_files(cidc_api)

    client = cidc_api.test_client()

    # A query missing the required parameters should yield 422
    res = client.get("/downloadable_files/download_url")
    assert res.status_code == 422
    assert res.json["_error"]["message"]["query"]["id"] == [
        "Missing data for required field."
    ]

    # A missing file should yield 404
    res = client.get("/downloadable_files/download_url?id=123212321")
    assert res.status_code == 404

    # No permission should also yield 404
    res = client.get(f"/downloadable_files/download_url?id={file_id}")
    assert res.status_code == 404

    with cidc_api.app_context():
        perm = Permissions(
            granted_to_user=user_id, trial_id=trial_id, upload_type=upload_types[0]
        )
        perm.insert()

    test_url = "foo"
    monkeypatch.setattr(
        "cidc_api.shared.gcloud_client.get_signed_url", lambda *args: test_url
    )

    res = client.get(f"/downloadable_files/download_url?id={file_id}")
    assert res.status_code == 200
    assert res.json == test_url
