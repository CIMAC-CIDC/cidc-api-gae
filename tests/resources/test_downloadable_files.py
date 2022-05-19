import os

os.environ["TZ"] = "UTC"
from datetime import datetime
import logging
from typing import Tuple
from unittest.mock import MagicMock, call

from cidc_api.models import (
    Users,
    DownloadableFiles,
    TrialMetadata,
    Permissions,
    CIDCRole,
)
from cidc_api.config.settings import GOOGLE_ACL_DATA_BUCKET
from cidc_api.resources.upload_jobs import log_multiple_errors

from ..utils import mock_current_user, make_admin, make_role, mock_gcloud_client


def setup_user(cidc_api, monkeypatch) -> int:
    # this is necessary for adding/removing permissions from this user
    # without trying to contact GCP
    mock_gcloud_client(monkeypatch)

    current_user = Users(
        email="test@email.com",
        role=CIDCRole.CIMAC_USER.value,
        approval_date=datetime.now(),
    )
    mock_current_user(current_user, monkeypatch)

    with cidc_api.app_context():
        current_user.insert()
        return current_user.id


trial_id_1 = "test-trial-1"
trial_id_2 = "test-trial-2"
upload_types = ["wes_bam", "cytof"]


def setup_downloadable_files(cidc_api) -> Tuple[int, int]:
    """Insert two downloadable files into the database."""
    metadata_json = {
        "protocol_identifier": trial_id_1,
        "allowed_collection_event_names": [],
        "allowed_cohort_names": [],
        "participants": [],
    }
    trial_1 = TrialMetadata(trial_id=trial_id_1, metadata_json=metadata_json)
    trial_2 = TrialMetadata(trial_id=trial_id_2, metadata_json=metadata_json)

    def make_file(trial_id, object_url, upload_type, facet_group) -> DownloadableFiles:
        return DownloadableFiles(
            trial_id=trial_id,
            upload_type=upload_type,
            object_url=f"{trial_id}/{object_url}",
            facet_group=facet_group,
            uploaded_timestamp=datetime.now(),
            file_size_bytes=int(51 * 1e6),  # 51MB
        )

    wes_file = make_file(
        trial_id_1, "wes/.../reads_123.bam", "wes_bam", "/wes/r1_L.fastq.gz"
    )
    cytof_file = make_file(
        trial_id_2, "cytof/.../analysis.zip", "cytof", "/cytof_analysis/analysis.zip"
    )

    with cidc_api.app_context():
        trial_1.insert()
        trial_2.insert()
        wes_file.insert()
        cytof_file.insert()

        return wes_file.id, cytof_file.id


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

    # Test a couple different permission configurations that should
    # produce the same result in this case.
    for kwargs in [
        {"trial_id": trial_id_1, "upload_type": upload_types[0]},
        {"upload_type": upload_types[0]},
        {"trial_id": trial_id_1},
    ]:
        # Give the user one permission
        with cidc_api.app_context():
            perm = Permissions(
                granted_to_user=user_id, granted_by_user=user_id, **kwargs
            )
            perm.insert()

        # Non-admins can view files for which they have permission
        res = client.get("/downloadable_files")
        assert res.status_code == 200
        assert len(res.json["_items"]) == 1
        assert res.json["_meta"]["total"] == 1
        assert res.json["_items"][0]["id"] == file_id_1

    # Non-admin filter queries exclude files they aren't allowed to view
    res = client.get(f"/downloadable_files?facets=Assay Type|CyTOF|Analysis Results")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 0
    assert res.json["_meta"]["total"] == 0

    # Admins and NCI biobank users can view all files regardless of their permissions
    for role in [CIDCRole.ADMIN.value, CIDCRole.NCI_BIOBANK_USER.value]:
        make_role(user_id, role, cidc_api)
        res = client.get("/downloadable_files")
        assert res.status_code == 200
        assert len(res.json["_items"]) == 2
        assert res.json["_meta"]["total"] == 2
        assert set([f["id"] for f in res.json["_items"]]) == set([file_id_1, file_id_2])

        # Admin filter queries include any files that fit the criteria
        res = client.get(
            f"/downloadable_files?facets=Assay Type|CyTOF|Analysis Results"
        )
        assert res.status_code == 200
        assert len(res.json["_items"]) == 1
        assert res.json["_meta"]["total"] == 1
        assert res.json["_items"][0]["id"] == file_id_2

    # Make sure it's possible to sort by file extension
    res = client.get(f"/downloadable_files?sort_field=file_ext&sort_direction=asc")
    assert res.status_code == 200
    assert [f["file_ext"] for f in res.json["_items"]] == ["bam", "zip"]

    # Make sure it's possible to sort by data category
    res = client.get(f"/downloadable_files?sort_field=data_category&sort_direction=asc")
    assert res.status_code == 200
    assert [f["data_category"] for f in res.json["_items"]] == [
        "CyTOF|Analysis Results",
        "WES|Source",
    ]


def test_get_downloadable_file(cidc_api, clean_db, monkeypatch):
    """Check that getting a single file works as expected."""
    user_id = setup_user(cidc_api, monkeypatch)
    file_id_1, file_id_2 = setup_downloadable_files(cidc_api)

    client = cidc_api.test_client()

    # Non-admins get 401s for single files they don't have permision to view
    res = client.get(f"/downloadable_files/{file_id_1}")
    assert res.status_code == 401

    # Give the user one permission
    with cidc_api.app_context():
        perm = Permissions(
            granted_to_user=user_id,
            trial_id=trial_id_1,
            upload_type=upload_types[0],
            granted_by_user=user_id,
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


def test_get_related_files(cidc_api, clean_db, monkeypatch):
    """Check that the related_files endpoint calls `get_related_files`"""
    user_id = setup_user(cidc_api, monkeypatch)
    file_id_1, file_id_2 = setup_downloadable_files(cidc_api)

    client = cidc_api.test_client()

    # Add an additional file that is related to file 1
    object_url = "/foo/bar"
    with cidc_api.app_context():
        DownloadableFiles(
            trial_id=trial_id_1,
            upload_type="wes",
            object_url=object_url,
            facet_group="/wes/r2_L.fastq.gz",  # this is what makes this file "related"
            uploaded_timestamp=datetime.now(),
            file_size_bytes=0,
        ).insert()

    # Non-admins get 401s when requesting related files they don't have permission to view
    res = client.get(f"/downloadable_files/{file_id_1}/related_files")
    assert res.status_code == 401

    # Give the user one permission
    with cidc_api.app_context():
        perm = Permissions(
            granted_to_user=user_id,
            trial_id=trial_id_1,
            upload_type=upload_types[0],
            granted_by_user=user_id,
        )
        perm.insert()

    # Non-admins can get related files that they have permision to view
    res = client.get(f"/downloadable_files/{file_id_1}/related_files")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 1  # file 1 has 1 related file
    assert res.json["_items"][0]["object_url"] == object_url

    # Admins can get related files without permissions
    make_admin(user_id, cidc_api)
    res = client.get(f"/downloadable_files/{file_id_2}/related_files")
    assert res.status_code == 200
    assert len(res.json["_items"]) == 0  # file 2 has 0 related file


def test_get_filelist(cidc_api, clean_db, monkeypatch):
    """Check that getting a filelist.tsv works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    file_id_1, file_id_2 = setup_downloadable_files(cidc_api)

    client = cidc_api.test_client()

    url = "/downloadable_files/filelist"

    # A JSON body containing a file ID list must be provided
    res = client.post(url)
    assert res.status_code == 422

    # User has no permissions, so no files should be found
    short_file_list = {"file_ids": [file_id_1, file_id_2]}
    res = client.post(url, json=short_file_list)
    assert res.status_code == 404

    # Give the user one permission
    with cidc_api.app_context():
        perm = Permissions(
            granted_to_user=user_id,
            trial_id=trial_id_1,
            upload_type=upload_types[0],
            granted_by_user=user_id,
        )
        perm.insert()

    # User has one permission, so the filelist should contain a single file
    res = client.post(url, json=short_file_list)
    assert res.status_code == 200
    assert "text/tsv" in res.headers["Content-Type"]
    assert "filename=filelist.tsv" in res.headers["Content-Disposition"]
    assert res.data.decode("utf-8") == (
        f"gs://{GOOGLE_ACL_DATA_BUCKET}/{trial_id_1}/wes/.../reads_123.bam\t{trial_id_1}_wes_..._reads_123.bam\n"
    )

    # Admins don't need permissions to get files
    make_admin(user_id, cidc_api)
    res = client.post(url, json=short_file_list)
    assert res.status_code == 200

    assert res.data.decode("utf-8") in [
        (
            f"gs://{GOOGLE_ACL_DATA_BUCKET}/{trial_id_1}/wes/.../reads_123.bam\t{trial_id_1}_wes_..._reads_123.bam\n"
            f"gs://{GOOGLE_ACL_DATA_BUCKET}/{trial_id_2}/cytof/.../analysis.zip\t{trial_id_2}_cytof_..._analysis.zip\n"
        ),
        (  # reversed
            f"gs://{GOOGLE_ACL_DATA_BUCKET}/{trial_id_2}/cytof/.../analysis.zip\t{trial_id_2}_cytof_..._analysis.zip\n"
            f"gs://{GOOGLE_ACL_DATA_BUCKET}/{trial_id_1}/wes/.../reads_123.bam\t{trial_id_1}_wes_..._reads_123.bam\n"
        ),
    ]

    # Clear inserted file records
    with cidc_api.app_context():
        clean_db.query(DownloadableFiles).delete()

    # Filelists don't get paginated
    ids = []
    with cidc_api.app_context():
        for id in range(1000):
            df = DownloadableFiles(
                trial_id=trial_id_1,
                object_url=str(id),
                upload_type="",
                file_size_bytes=0,
                facet_group="foobar",
                uploaded_timestamp=datetime.now(),
            )
            df.insert()
            ids.append(df.id)

    res = client.post(url, json={"file_ids": ids})
    assert res.status_code == 200
    # newly inserted files + EOF newline
    assert len(res.data.decode("utf-8").split("\n")) == len(ids) + 1


def test_create_compressed_batch(cidc_api, clean_db, monkeypatch):
    user_id = setup_user(cidc_api, monkeypatch)
    file_id_1, file_id_2 = setup_downloadable_files(cidc_api)
    with cidc_api.app_context():
        url_1 = DownloadableFiles.find_by_id(file_id_1).object_url
        url_2 = DownloadableFiles.find_by_id(file_id_2).object_url

    client = cidc_api.test_client()

    url = "/downloadable_files/compressed_batch"

    # A JSON body containing a file ID list must be provided
    res = client.post(url)
    assert res.status_code == 422

    # User has no permissions, so no files should be found
    short_file_list = {"file_ids": [file_id_1, file_id_2]}
    res = client.post(url, json=short_file_list)
    assert res.status_code == 404

    # Give the user one permission
    with cidc_api.app_context():
        perm = Permissions(
            granted_to_user=user_id,
            trial_id=trial_id_1,
            upload_type=upload_types[0],
            granted_by_user=user_id,
        )
        perm.insert()

    # Mock GCS client and loger
    blob = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    monkeypatch.setattr(
        "cidc_api.resources.downloadable_files.gcloud_client._get_bucket",
        lambda _: bucket,
    )
    signed_url = "fake/signed/url"
    monkeypatch.setattr(
        "cidc_api.resources.downloadable_files.gcloud_client.get_signed_url",
        lambda *_: signed_url,
    )

    mock_logger = MagicMock()
    monkeypatch.setattr("cidc_api.resources.downloadable_files.logger", mock_logger)

    # User has one permission, s0 the endpoint should try to create
    # a compressed batch file with the single file the user has
    # access to in it.
    res = client.post(url, json=short_file_list)
    assert res.status_code == 200
    assert res.json == signed_url
    print(bucket.get_blob.call_args_list)
    bucket.get_blob.assert_called_with(url_1)
    blob.upload_from_filename.assert_called_once()

    mock_logger.info.assert_called_once()
    assert "test@email.com" in mock_logger.info.call_args[0][0]
    assert url_1 in mock_logger.info.call_args[0][0]

    bucket.reset_mock()
    blob.reset_mock()
    mock_logger.reset_mock()

    make_admin(user_id, cidc_api)

    # Admin has access to both files, but together they are too large
    res = client.post(url, json=short_file_list)
    assert res.status_code == 400
    assert "batch too large" in res.json["_error"]["message"]
    bucket.get_blob.assert_not_called()
    blob.upload_from_filename.assert_not_called()

    # Decrease the size of one of the files and try again
    with cidc_api.app_context():
        df = DownloadableFiles.find_by_id(file_id_1)
        df.file_size_bytes = 1
        df.update()

    res = client.post(url, json=short_file_list)
    assert res.status_code == 200
    assert res.json == signed_url
    assert call(url_1) in bucket.get_blob.call_args_list
    assert call(url_2) in bucket.get_blob.call_args_list
    blob.upload_from_filename.assert_called_once()

    mock_logger.info.assert_called_once()
    assert "test@email.com" in mock_logger.info.call_args[0][0]
    assert url_1 in mock_logger.info.call_args[0][0]
    assert url_2 in mock_logger.info.call_args[0][0]


def test_get_filter_facets(cidc_api, clean_db, monkeypatch):
    """Check that getting filter facets works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    setup_downloadable_files(cidc_api)

    client = cidc_api.test_client()

    def check_facet_counts(facets, wes_count=0, cytof_count=0):
        for facet, subfacets in facets["Assay Type"].items():
            if not isinstance(subfacets, list):
                subfacets = [subfacets]
            for subfacet in subfacets:
                if facet == "WES" and subfacet["label"] == "Source":
                    assert subfacet["count"] == wes_count
                elif facet == "CyTOF" and subfacet["label"] == "Analysis Results":
                    assert subfacet["count"] == cytof_count
                else:
                    assert subfacet["count"] == 0

    # Non-admins' facets take into account their permissions
    with cidc_api.app_context():
        perm = Permissions(
            granted_to_user=user_id,
            trial_id=trial_id_1,
            upload_type=upload_types[0],
            granted_by_user=user_id,
        )
        perm.insert()
    res = client.get("/downloadable_files/filter_facets")
    assert res.status_code == 200
    check_facet_counts(res.json["facets"], wes_count=1, cytof_count=0)

    # Admins' facets include all files, regardless of permissions
    make_admin(user_id, cidc_api)
    res = client.get("/downloadable_files/filter_facets")
    assert res.status_code == 200
    assert sorted(res.json["trial_ids"], key=lambda x: x["label"]) == sorted(
        [{"label": trial_id_1, "count": 1}, {"label": trial_id_2, "count": 1}],
        key=lambda x: x["label"],
    )
    check_facet_counts(res.json["facets"], wes_count=1, cytof_count=1)

    # Trial facets are governed by data category facets
    res = client.get("/downloadable_files/filter_facets?facets=Assay Type|WES|Germline")
    assert res.status_code == 200
    assert res.json["trial_ids"] == []
    check_facet_counts(res.json["facets"], wes_count=1, cytof_count=1)

    # Data category facets are governed by trial facets
    res = client.get("/downloadable_files/filter_facets?trial_ids=someothertrial")
    assert res.status_code == 200
    res.json["trial_ids"] == []
    check_facet_counts(res.json["facets"], wes_count=0, cytof_count=0)


def test_get_download_url(cidc_api, clean_db, monkeypatch):
    """Check that generating a GCS signed URL works as expected"""
    user_id = setup_user(cidc_api, monkeypatch)
    file_id, _ = setup_downloadable_files(cidc_api)
    with cidc_api.app_context():
        file_url = DownloadableFiles.find_by_id(file_id).object_url

    # mock logs
    mock_logger = MagicMock()
    monkeypatch.setattr("cidc_api.resources.downloadable_files.logger", mock_logger)

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
            granted_to_user=user_id,
            trial_id=trial_id_1,
            upload_type=upload_types[0],
            granted_by_user=user_id,
        )
        perm.insert()

    test_url = "foo"
    monkeypatch.setattr(
        "cidc_api.shared.gcloud_client.get_signed_url", lambda *args: test_url
    )

    res = client.get(f"/downloadable_files/download_url?id={file_id}")
    assert res.status_code == 200
    assert res.json == test_url
    mock_logger.info.assert_called_once()
    assert "test@email.com" in mock_logger.info.call_args[0][0]
    assert file_url in mock_logger.info.call_args[0][0]

    # network viewers aren't allowed to get download urls
    make_role(user_id, CIDCRole.NETWORK_VIEWER.value, cidc_api)
    res = client.get(f"/downloadable_files/download_url?id={file_id}")
    assert res.status_code == 401


def test_log_multiple_errors(caplog):
    """Check that the log_multiple_errors function doesn't throw an error itself."""
    caplog.set_level(logging.DEBUG)

    # Empty list
    log_multiple_errors([])
    assert caplog.text == ""
    caplog.clear()

    # Multiple data types
    log_multiple_errors([0, {"some": "error"}, "uh oh"])
    assert "0" in caplog.text
    assert "{'some': 'error'}" in caplog.text
    assert "uh oh" in caplog.text
    caplog.clear()

    # Non-list
    log_multiple_errors("some error")
    assert "some error" in caplog.text
    caplog.clear()


def test_facet_groups_for_links(cidc_api, clean_db, monkeypatch):
    user_id = setup_user(cidc_api, monkeypatch)
    setup_downloadable_files(cidc_api)

    client = cidc_api.test_client()

    res = client.get("/downloadable_files/facet_groups_for_links")
    assert res.status_code == 200
    facets = res.json["facets"]

    assert facets == {
        "clinical_participants": {
            "analyzed": [],
            "received": [
                "Clinical Type|Participants Info",
                "Clinical Type|Samples Info",
                "Clinical Type|Clinical Data",
            ],
        },
        "atacseq": {
            "analyzed": [
                "Assay Type|ATAC-Seq|Source",
                "Assay Type|ATAC-Seq|Peaks",
                "Assay Type|ATAC-Seq|Report",
            ],
            "received": ["Assay Type|ATAC-Seq|Source"],
        },
        "cytof": {
            "analyzed": [
                "Assay Type|CyTOF|Cell Counts",
                "Assay Type|CyTOF|Labeled Source",
                "Assay Type|CyTOF|Analysis Results",
                "Assay Type|CyTOF|Key",
            ],
            "received": [
                "Assay Type|CyTOF|Source",
                "Assay Type|CyTOF|Combined Cell Counts",
                "Analysis Ready|CyTOF",
            ],
        },
        "elisa": {
            "analyzed": [],
            "received": ["Assay Type|ELISA|Data"],
        },
        "h&e": {
            "analyzed": [],
            "received": ["Assay Type|H&E|Images"],
        },
        "ihc": {
            "analyzed": [],
            "received": [
                "Assay Type|IHC|Images",
                "Assay Type|IHC|Combined Markers",
                "Analysis Ready|IHC",
            ],
        },
        "mif": {
            "analyzed": [],
            "received": [
                "Assay Type|mIF|Source Images",
                "Assay Type|mIF|Images with Features",
                "Assay Type|mIF|Analysis Images",
                "Assay Type|mIF|Analysis Data",
                "Assay Type|mIF|QC Info",
                "Analysis Ready|mIF",
            ],
        },
        "miscellaneous": {
            "analyzed": [],
            "received": ["Assay Type|Miscellaneous|All"],
        },
        "nanostring": {
            "analyzed": [],
            "received": [
                "Assay Type|Nanostring|Source",
                "Assay Type|Nanostring|Data",
                "Analysis Ready|Nanostring",
            ],
        },
        "olink": {
            "analyzed": ["Assay Type|Olink|Study-Level", "Analysis Ready|Olink"],
            "received": [
                "Assay Type|Olink|Run-Level",
                "Assay Type|Olink|Batch-Level",
                "Assay Type|Olink|Study-Level",
            ],
        },
        "rna": {
            "analyzed": [
                "Assay Type|RNA|Alignment",
                "Assay Type|RNA|Quality",
                "Assay Type|RNA|Gene Quantification",
                "Assay Type|RNA|Microbiome",
                "Assay Type|RNA|Immune-Repertoire",
                "Assay Type|RNA|Fusion",
                "Assay Type|RNA|MSI",
                "Assay Type|RNA|HLA",
                "Analysis Ready|RNA",
            ],
            "received": ["Assay Type|RNA|Source"],
        },
        "tcr": {
            "analyzed": [
                "Assay Type|TCR|Misc.",
                "Assay Type|TCR|Analysis Data",
                "Assay Type|TCR|Reports",
                "Analysis Ready|TCR",
            ],
            "received": ["Assay Type|TCR|Source"],
        },
        "wes_normal": {
            "analyzed": [
                "Assay Type|WES|Germline",
                "Assay Type|WES|Purity",
                "Assay Type|WES|Clonality",
                "Assay Type|WES|Copy Number",
                "Assay Type|WES|Neoantigen",
                "Assay Type|WES|Somatic",
                "Assay Type|WES|Alignment",
                "Assay Type|WES|Metrics",
                "Assay Type|WES|HLA Type",
                "Assay Type|WES|Report",
                "Assay Type|WES|RNA",
                "Assay Type|WES|MSI",
                "Assay Type|WES|Error Documentation",
                "Analysis Ready|WES Analysis",
            ],
            "received": ["Assay Type|WES|Source", "Analysis Ready|WES Assay"],
        },
        "wes_tumor": {
            "analyzed": [
                "Assay Type|WES Tumor-Only|Germline",
                "Assay Type|WES Tumor-Only|Purity",
                "Assay Type|WES Tumor-Only|Clonality",
                "Assay Type|WES Tumor-Only|Copy Number",
                "Assay Type|WES Tumor-Only|Error Documentation",
                "Assay Type|WES Tumor-Only|Neoantigen",
                "Assay Type|WES Tumor-Only|Somatic",
                "Assay Type|WES Tumor-Only|Alignment",
                "Assay Type|WES Tumor-Only|Metrics",
                "Assay Type|WES Tumor-Only|HLA Type",
                "Assay Type|WES Tumor-Only|Report",
                "Assay Type|WES Tumor-Only|MSI",
            ],
            "received": ["Assay Type|WES|Source", "Analysis Ready|WES Assay"],
        },
    }
