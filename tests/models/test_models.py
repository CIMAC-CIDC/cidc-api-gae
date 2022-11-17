from copy import deepcopy
from deepdiff import DeepDiff
from typing import Dict, List
import pandas as pd
import io
import logging
from functools import wraps

import os

os.environ["TZ"] = "UTC"
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound

from cidc_api.app import app
from cidc_api.models import (
    CommonColumns,
    Users,
    TrialMetadata,
    UploadJobs,
    Permissions,
    DownloadableFiles,
    with_default_session,
    UploadJobStatus,
    NoResultFound,
    ValidationMultiError,
    CIDCRole,
)
from cidc_api.config.settings import (
    PAGINATION_PAGE_SIZE,
    MAX_PAGINATION_PAGE_SIZE,
    INACTIVE_USER_DAYS,
)
from cidc_schemas import prism

from ..utils import mock_gcloud_client


def db_test(test):
    """
    Wrap a test function in an application context.
    """

    @wraps(test)
    def wrapped(*args, **kwargs):
        with app.app_context():
            test(*args, **kwargs)

    return wrapped


EMAIL = "test@email.com"
PROFILE = {"email": EMAIL}


def test_common_compute_etag():
    """Check that compute_etag excludes private fields"""

    u = Users()

    # Updates to private fields shouldn't change the etag
    etag = u.compute_etag()
    u._updated = datetime.now()
    assert u.compute_etag() == etag

    # Updates to public fields should change the etag
    u.first_n = "foo"
    new_etag = u.compute_etag()
    assert new_etag != etag
    u.first_n = "buzz"
    assert u.compute_etag() != new_etag

    # Compute etag returns the same result if `u` doesn't change
    assert u.compute_etag() == u.compute_etag()


@db_test
def test_common_insert(clean_db):
    """Test insert, inherited from CommonColumns"""
    # Check disabling committing
    u1 = Users(email="a")
    u1.insert(commit=False)
    assert not u1.id

    # Insert a new record without disabling committing
    u2 = Users(email="b")
    u2.insert()
    assert u1.id and u1._etag
    assert u2.id and u2._etag
    assert u1._etag != u2._etag

    assert Users.find_by_id(u1.id)
    assert Users.find_by_id(u2.id)


@db_test
def test_common_update(clean_db):
    """Test update, inherited from CommonColumns"""
    email = "foo"
    user = Users(id=1, email=email)

    # Record not found
    with pytest.raises(NoResultFound):
        user.update()

    user.insert()

    _updated = user._updated

    # Update via setattr and changes
    first_n = "hello"
    last_n = "goodbye"
    user.last_n = last_n
    user.update(changes={"first_n": first_n})
    user = Users.find_by_id(user.id)
    assert user._updated > _updated
    assert user.first_n == first_n
    assert user.last_n == last_n

    _updated = user._updated
    _etag = user._etag

    # Make sure you can clear a field to null
    user.update(changes={"first_n": None})
    user = Users.find_by_id(user.id)
    assert user._updated > _updated
    assert _etag != user._etag
    assert user.first_n is None

    _updated = user._updated
    _etag = user._etag

    # Make sure etags don't change if public fields don't change
    user.update()
    user = Users.find_by_id(user.id)
    assert user._updated > _updated
    assert _etag == user._etag


@db_test
def test_common_delete(clean_db):
    """Test delete, inherited from CommonColumns"""
    user1 = Users(email="foo")
    user2 = Users(email="bar")

    # Try to delete an uninserted record
    with pytest.raises(InvalidRequestError):
        user1.delete()

    user1.insert()
    user2.insert()

    # Defer a deletion with commit=False
    user1.delete(commit=False)
    assert Users.find_by_id(user1.id)

    # Delete with auto-commit
    user2.delete()
    assert not Users.find_by_id(user1.id)
    assert not Users.find_by_id(user2.id)


@db_test
def test_common_list(clean_db):
    """Test listing behavior, inherited from CommonColumns"""
    for i in range(105):
        name = f"user_{i}"
        Users(email=f"{name}@example.com", first_n=name).insert()

    # List with defaults
    user_list = Users.list()
    assert len(user_list) == PAGINATION_PAGE_SIZE

    # List with different pagination size
    short_list = Users.list(page_size=5)
    assert len(short_list) == 5

    # List with sorting
    sorted_list = Users.list(sort_field="id")
    assert sorted_list[0].first_n == "user_104"
    first_page = Users.list(sort_field="id", sort_direction="asc")
    assert first_page[0].first_n == "user_0"
    sorted_list = Users.list(sort_field="first_n", sort_direction="asc")
    assert sorted_list[0].first_n == "user_0"

    # Get the second page
    second_page = Users.list(page_num=1, sort_field="id", sort_direction="asc")
    assert second_page[0].first_n == "user_25"
    assert second_page[-1].first_n == "user_49"

    # Get the last page
    last_page = Users.list(page_num=4, sort_field="id", sort_direction="asc")
    assert len(last_page) == 5

    # Get a negative page
    negative_page = Users.list(page_num=-1, sort_field="id", sort_direction="asc")
    assert set(n.id for n in negative_page) == set(f.id for f in first_page)

    # Get a too-high page
    too_high_page = Users.list(page_num=100, sort_field="id", sort_direction="asc")
    assert len(too_high_page) == 0

    # Add a filter
    def f(q):
        return q.filter(Users.first_n.like("%9%"))

    all_expected_values = set(f"user_{i}" for i in range(100) if "9" in str(i))
    filtered_page = Users.list(
        filter_=f, page_num=0, sort_field="id", sort_direction="asc"
    )
    assert all_expected_values == set(f.first_n for f in filtered_page)

    # Get a too-large page
    for i in range(106, 300):
        name = f"user_{i}"
        Users(email=f"{name}@example.com", first_n=name).insert()
    big_page = Users.list(page_size=1e10)
    assert len(big_page) == MAX_PAGINATION_PAGE_SIZE


@db_test
def test_common_count(clean_db):
    """Test counting behavior, inherited from CommonColumns"""
    num = 105
    for i in range(num):
        name = f"user_{i}"
        Users(email=f"{name}@example.com", first_n=name).insert()

    # Count without filter
    assert Users.count() == num

    # Count with filter
    def f(q):
        return q.filter(Users.first_n.like("%9%"))

    num_expected = len(list(f"user_{i}" for i in range(100) if "9" in str(i)))
    assert Users.count(filter_=f) == num_expected


@db_test
def test_create_user(clean_db):
    """Try to create a user that doesn't exist"""
    Users.create(PROFILE)
    user = Users.find_by_email(EMAIL)
    assert user
    assert user.email == EMAIL


@db_test
def test_duplicate_user(clean_db):
    """Ensure that a user won't be created twice"""
    Users.create(PROFILE)
    Users.create(PROFILE)
    assert clean_db.query(Users).count() == 1


@db_test
def test_disable_inactive_users(clean_db, monkeypatch):
    """Check that the disable_inactive_users method disables users appropriately"""
    revoke_user_permissions = MagicMock()
    revoke_bigquery_access = MagicMock()
    monkeypatch.setattr(
        "cidc_api.models.models.Permissions.revoke_user_permissions",
        revoke_user_permissions,
    )
    monkeypatch.setattr(
        "cidc_api.models.models.revoke_bigquery_access",
        revoke_bigquery_access,
    )

    # Create two users who should be disabled, and one who should not
    now = datetime.now()
    Users(email="1@", _accessed=now - timedelta(days=INACTIVE_USER_DAYS)).insert()
    Users(email="2@", _accessed=now - timedelta(days=INACTIVE_USER_DAYS + 5)).insert()
    Users(email="3@", _accessed=now - timedelta(days=INACTIVE_USER_DAYS - 1)).insert()
    Users(
        email="4@",
        _accessed=now - timedelta(days=INACTIVE_USER_DAYS - 1),
        disabled=True,
    ).insert()

    # 3 users start off enabled
    # 1 starts disabled to test that not returned for CFn email
    for user in Users.list():
        if user.email != "4@":
            assert user.disabled == False

    disabled = Users.disable_inactive_users(session=clean_db)

    # Remember, 4@ was already disabled
    assert len(disabled) == 2

    users = Users.list()
    assert len([u for u in users if u.disabled]) == len(disabled) + 1
    assert sorted(["1@", "2@"]) == sorted(disabled)
    assert [u.email for u in users if not u.disabled] == ["3@"]

    assert revoke_user_permissions.call_count == 2
    assert revoke_bigquery_access.call_count == 2


TRIAL_ID = "cimac-12345"
METADATA = {
    prism.PROTOCOL_ID_FIELD_NAME: TRIAL_ID,
    "participants": [],
    "allowed_cohort_names": ["Arm_Z"],
    "allowed_collection_event_names": [],
}


@db_test
def test_create_trial_metadata(clean_db):
    """Insert a trial metadata record if one doesn't exist"""
    TrialMetadata.create(TRIAL_ID, METADATA)
    trial = TrialMetadata.find_by_trial_id(TRIAL_ID)
    assert trial
    assert trial.metadata_json == METADATA

    # Check that you can't insert a trial with invalid metadata
    with pytest.raises(ValidationMultiError, match="'buzz' was unexpected"):
        TrialMetadata.create("foo", {"buzz": "bazz"})

    with pytest.raises(ValidationMultiError, match="'buzz' was unexpected"):
        TrialMetadata(trial_id="foo", metadata_json={"buzz": "bazz"}).insert()


@db_test
def test_trial_metadata_insert(clean_db):
    """Test that metadata validation on insert works as expected"""
    # No error with valid metadata
    trial = TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA)
    trial.insert()

    # Error with invalid metadata
    trial.metadata_json = {"foo": "bar"}
    with pytest.raises(ValidationMultiError):
        trial.insert()

    # No error if validate_metadata=False
    trial.insert(validate_metadata=False)


@db_test
def test_trial_metadata_update(clean_db):
    """Test that metadata validation on update works as expected"""
    trial = TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA)
    trial.insert()

    # No error on valid `changes` update
    trial.update(changes={"metadata_json": {**METADATA, "nct_id": "foo"}})

    # No error on valid attribute update
    trial.metadata_json = {**METADATA, "nct_id": "bar"}
    trial.update()

    bad_json = {"metadata_json": {"foo": "bar"}}

    # Error on invalid `changes` update
    with pytest.raises(ValidationMultiError):
        trial.update(changes=bad_json)

    # No error on invalid `changes` update if validate_metadata=False
    trial.update(changes=bad_json, validate_metadata=False)

    # Error on invalid attribute update
    trial.metadata_json = bad_json
    with pytest.raises(ValidationMultiError):
        trial.update()

    # No error on invalid attribute update if validate_metadata=False
    trial.update(validate_metadata=False)


@db_test
def test_trial_metadata_patch_manifest(clean_db):
    """Update manifest data in a trial_metadata record"""
    # Add a participant to the trial
    metadata_with_participant = METADATA.copy()
    metadata_with_participant["participants"] = [
        {
            "samples": [],
            "cimac_participant_id": "CTSTP01",
            "participant_id": "trial a",
            "cohort_name": "Arm_Z",
        }
    ]

    with pytest.raises(NoResultFound, match=f"No trial found with id {TRIAL_ID}"):
        TrialMetadata.patch_manifest(TRIAL_ID, metadata_with_participant)

    # Create trial
    TrialMetadata.create(TRIAL_ID, METADATA)

    # Try again
    TrialMetadata.patch_manifest(TRIAL_ID, metadata_with_participant)

    # Look the trial up and check that it has the participant in it
    trial = TrialMetadata.find_by_trial_id(TRIAL_ID)
    assert (
        trial.metadata_json["participants"] == metadata_with_participant["participants"]
    )


@db_test
def test_trial_metadata_patch_assay(clean_db):
    """Update assay data in a trial_metadata record"""
    # Add an assay to the trial
    metadata_with_assay = METADATA.copy()
    metadata_with_assay["assays"] = {"wes": []}

    with pytest.raises(NoResultFound, match=f"No trial found with id {TRIAL_ID}"):
        TrialMetadata.patch_manifest(TRIAL_ID, metadata_with_assay)

    # Create trial
    TrialMetadata.create(TRIAL_ID, METADATA)

    # Try again
    TrialMetadata.patch_manifest(TRIAL_ID, metadata_with_assay)

    # Look the trial up and check that it has the assay in it
    trial = TrialMetadata.find_by_trial_id(TRIAL_ID)
    assert trial.metadata_json["assays"] == metadata_with_assay["assays"]


@db_test
def test_partial_patch_trial_metadata(clean_db):
    """Update an existing trial_metadata_record"""
    # Create the initial trial

    TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA).insert(session=clean_db)

    # Create patch without all required fields (no "participants")
    metadata_patch = {prism.PROTOCOL_ID_FIELD_NAME: TRIAL_ID, "assays": {}}

    # patch it - should be no error/exception
    TrialMetadata._patch_trial_metadata(TRIAL_ID, metadata_patch)


@db_test
def test_trial_metadata_get_summaries(clean_db, monkeypatch):
    """Check that trial data summaries are computed as expected"""

    def int_to_cimac_id(num: int) -> str:
        ret = "".join(["ABCDEFGHIJ"[int(d)] for d in str(num)])
        to_add = max(0, 6 - len(ret))
        return "C" + "0" * to_add + ret + "00.01"

    # Add some trials
    def make_records(start: int, end: int, **kwargs) -> List[Dict[str, str]]:
        ret = [{"cimac_id": int_to_cimac_id(i)} for i in range(start, end)]
        [r.update(kwargs) for r in ret]
        return ret

    tm1 = {
        **METADATA,
        # deliberately override METADATA['protocol_identifier']
        "protocol_identifier": "tm1",
        "participants": [
            {
                "samples": [
                    {
                        "cimac_id": "C000000T1",
                        "processed_sample_derivative": "Tumor DNA",
                    },
                    {
                        "cimac_id": "C000000T2",
                        "processed_sample_derivative": "Tumor DNA",
                    },
                    {"cimac_id": "C000000N1", "processed_sample_derivative": "not"},
                    {"cimac_id": "C000000N2", "processed_sample_derivative": "not"},
                ]
            },
            {
                "samples": [
                    {
                        "cimac_id": "C000000T3",
                        "processed_sample_derivative": "Tumor DNA",
                    },
                    {
                        "cimac_id": "C000000T4",
                        "processed_sample_derivative": "Tumor DNA",
                    },
                    {"cimac_id": "C000000N3", "processed_sample_derivative": "not"},
                ]
            },
        ],
        "expected_assays": ["ihc", "olink"],
        "assays": {
            "atacseq": [{"records": make_records(0, 13)}],  # 13 samples, 13 partics
            "ctdna": [{"records": make_records(0, 3)}],  # 0 new samples, 0 new partics
            "wes": [
                # wes_tumor_only = 1, wes = 3
                {
                    "records": [
                        {"cimac_id": f"C000000T{n}"} for n in range(1, 5)
                    ]  # 4 samples, 1 new partic
                    + [
                        {"cimac_id": f"C000000N{n}"} for n in range(1, 4)
                    ]  # 3 samples, 0 new partic
                },
            ],
            "rna": [{"records": make_records(0, 2)}],  # 0 new samples, 0 new partics
            "mif": [  # 0 new samples, 0 new partics
                {"records": make_records(0, 3)},
                {"records": make_records(3, 4)},
                {"records": make_records(4, 5)},
            ],
            "elisa": [
                {  # 0 new samples, 0 new partics
                    "assay_xlsx": {"samples": [int_to_cimac_id(i) for i in range(7)]}
                }
            ],
            "nanostring": [  # 0 new samples, 0 new partics
                {"runs": [{"samples": make_records(0, 2)}]},
                {"runs": [{"samples": make_records(2, 3)}]},
            ],
            "hande": [{"records": make_records(0, 5)}],  # 0 new samples, 0 new partics
        },
        "analysis": {
            # not checked for samples, partics
            "atacseq_analysis": [{"records": make_records(0, 12)}],
            "wes_analysis": {
                "pair_runs": [
                    {
                        "tumor": {"cimac_id": "C000000T1"},
                        "normal": {"cimac_id": "C000000N1"},
                    },  # no analysis data
                    # wes_analysis = 2; 1 here, 1 below
                    {
                        "tumor": {"cimac_id": "C000000T2"},
                        "normal": {"cimac_id": "C000000N2"},
                        "report": {"report": "foo"},
                    },
                ],
                # these are excluded, so not adding fake assay data
                "excluded_samples": make_records(0, 1),
            },
            "wes_analysis_old": {
                "pair_runs": [
                    # wes_analysis = 2; 1 here, 1 above
                    {
                        "tumor": {"cimac_id": "C000000T3"},
                        "normal": {"cimac_id": "C000000N3"},
                        "report": {"report": "foo"},
                    },
                ],
                # these are excluded, so not adding fake assay data
                "excluded_samples": make_records(1, 2),
            },
            "wes_tumor_only_analysis": {
                "runs": [
                    # wes_tumor_only_analysis = 2; 1 here, 1 below
                    {
                        "tumor": {"cimac_id": "C000000T4"},
                        "report": {"report": "foo"},
                    },
                ],
            },
            "wes_tumor_only_analysis_old": {
                "runs": [
                    # wes_tumor_only_analysis = 2; 1 here, 1 above
                    {
                        "tumor": {"cimac_id": "C000000T5"},
                        "report": {"report": "foo"},
                    },
                ],
            },
        },
        "clinical_data": {
            # not checked for samples, partics
            "records": [
                {"clinical_file": {"participants": ["a", "b", "c"]}},
                {"clinical_file": {"participants": ["a", "b", "d"]}},
                {"clinical_file": {"participants": ["e", "f", "g"]}},
            ]
        },
    }
    tm2 = {
        **METADATA,
        # deliberately override METADATA['protocol_identifier']
        "protocol_identifier": "tm2",
        "participants": [{"samples": []}],
        "assays": {
            "cytof": [
                # 5 samples, 5 participants
                {
                    "records": make_records(0, 2, output_files={"foo": "bar"}),
                    "excluded_samples": make_records(0, 2),
                },
                {"records": make_records(2, 4)},
                {"records": make_records(4, 5)},
            ],
            "olink": {  # 3 new samples, 3 new partics
                "batches": [
                    {
                        "records": [
                            {
                                "files": {
                                    "assay_npx": {
                                        "samples": [
                                            int_to_cimac_id(i) for i in range(2)
                                        ]
                                    }
                                }
                            },
                            {
                                "files": {
                                    "assay_npx": {
                                        "samples": [
                                            int_to_cimac_id(i) for i in range(2, 5)
                                        ]
                                    }
                                }
                            },
                        ]
                    },
                    {
                        "records": [
                            {
                                "files": {
                                    "assay_npx": {
                                        "samples": [
                                            int_to_cimac_id(i) for i in range(5, 8)
                                        ]
                                    }
                                }
                            }
                        ]
                    },
                ]
            },
        },
        "analysis": {
            # not checked for samples, partics
            "rna_analysis": {
                "level_1": make_records(0, 10),
                "excluded_samples": make_records(0, 2),
            },
            "tcr_analysis": {
                "batches": [
                    {
                        "records": make_records(0, 4),
                        "excluded_samples": make_records(0, 3),
                    },
                    {
                        "records": make_records(4, 6),
                        "excluded_samples": make_records(3, 4),
                    },
                ]
            },
            "cytof_analysis": {
                "batches": [
                    {
                        "records": make_records(0, 2),
                        "excluded_samples": make_records(0, 2),
                    }
                ]
            },
        },
    }
    TrialMetadata(trial_id="tm1", metadata_json=tm1).insert(validate_metadata=False)
    TrialMetadata(trial_id="tm2", metadata_json=tm2).insert(validate_metadata=False)

    # Add some files
    for i, (tid, fs) in enumerate([("tm1", 3), ("tm1", 2), ("tm2", 4), ("tm2", 6)]):
        DownloadableFiles(
            trial_id=tid,
            file_size_bytes=fs,
            object_url=str(i),
            facet_group="",
            uploaded_timestamp=datetime.now(),
            upload_type="",
        ).insert()

    sorter = lambda s: s["trial_id"]
    received = sorted(TrialMetadata.get_summaries(), key=sorter)
    expected = sorted(
        [
            {
                "trial_id": "tm2",
                "file_size_bytes": 10,
                "total_participants": 8,
                "total_samples": 8,
                "expected_assays": [],
                "atacseq": 0.0,
                "atacseq_analysis": 0.0,
                "clinical_participants": 0,
                "ctdna": 0.0,
                "cytof": 5.0,
                "cytof_analysis": 2.0,
                "elisa": 0.0,
                "h&e": 0.0,
                "mif": 0.0,
                "nanostring": 0.0,
                "olink": 8.0,
                "rna": 0.0,
                "rna_level1_analysis": 10.0,
                "tcr_analysis": 6.0,
                "wes": 0.0,
                "wes_analysis": 0.0,
                "wes_tumor_only": 0.0,
                "wes_tumor_only_analysis": 0.0,
                "excluded_samples": {
                    "tcr_analysis": make_records(0, 4),
                    "rna_level1_analysis": make_records(0, 2),
                    "cytof_analysis": make_records(0, 2),
                },
            },
            {
                "trial_id": "tm1",
                "file_size_bytes": 5,
                "total_participants": 14,
                "total_samples": 20,
                "expected_assays": ["ihc", "olink"],
                "atacseq": 13.0,
                "atacseq_analysis": 12.0,
                "clinical_participants": 7,
                "ctdna": 3.0,
                "cytof": 0.0,
                "cytof_analysis": 0.0,
                "elisa": 7.0,
                "h&e": 5.0,
                "mif": 5.0,
                "nanostring": 3.0,
                "olink": 0.0,
                "rna": 2.0,
                "rna_level1_analysis": 0.0,
                "tcr_analysis": 0.0,
                "wes": 3.0,
                "wes_analysis": 2.0,  # combined with wes_analysis_old
                "wes_tumor_only": 1.0,
                "wes_tumor_only_analysis": 2.0,  # combined with wes_tumor_only_analysis_old
                "excluded_samples": {
                    "wes_analysis": make_records(
                        0, 2
                    ),  # combined with wes_analysis_old
                },
            },
        ],
        key=sorter,
    )
    for e, r in zip(expected, received):
        assert DeepDiff(e, r, ignore_order=True) == {}, e["trial_id"]
    assert all("misc_data" not in entry for entry in received)


@db_test
def test_create_assay_upload(clean_db):
    """Try to create an assay upload"""
    new_user = Users.create(PROFILE)

    gcs_file_map = {
        "my/first/wes/blob1/2019-08-30T15:51:38.450978": "test-uuid-1",
        "my/first/wes/blob2/2019-08-30T15:51:38.450978": "test-uuid-2",
    }
    metadata_patch = {prism.PROTOCOL_ID_FIELD_NAME: TRIAL_ID}
    gcs_xlsx_uri = "xlsx/assays/wes/12:0:1.5123095"

    # Should fail, since trial doesn't exist yet
    with pytest.raises(IntegrityError):
        UploadJobs.create("wes_bam", EMAIL, gcs_file_map, metadata_patch, gcs_xlsx_uri)
    clean_db.rollback()

    TrialMetadata.create(TRIAL_ID, METADATA)

    new_job = UploadJobs.create(
        "wes_bam", EMAIL, gcs_file_map, metadata_patch, gcs_xlsx_uri
    )
    job = UploadJobs.find_by_id_and_email(new_job.id, PROFILE["email"])
    assert len(new_job.gcs_file_map) == len(job.gcs_file_map)
    assert set(new_job.gcs_file_map) == set(job.gcs_file_map)
    assert job.status == "started"

    assert list(job.upload_uris_with_data_uris_with_uuids()) == [
        (
            "my/first/wes/blob1/2019-08-30T15:51:38.450978",
            "my/first/wes/blob1",
            "test-uuid-1",
        ),
        (
            "my/first/wes/blob2/2019-08-30T15:51:38.450978",
            "my/first/wes/blob2",
            "test-uuid-2",
        ),
    ]


@db_test
def test_upload_job_no_file_map(clean_db):
    """Try to create an assay upload"""
    new_user = Users.create(PROFILE)

    metadata_patch = {prism.PROTOCOL_ID_FIELD_NAME: TRIAL_ID}
    gcs_xlsx_uri = "xlsx/assays/wes/12:0:1.5123095"

    TrialMetadata.create(TRIAL_ID, METADATA)

    new_job = UploadJobs.create(
        prism.SUPPORTED_MANIFESTS[0], EMAIL, None, metadata_patch, gcs_xlsx_uri
    )
    assert list(new_job.upload_uris_with_data_uris_with_uuids()) == []

    job = UploadJobs.find_by_id_and_email(new_job.id, PROFILE["email"])
    assert list(job.upload_uris_with_data_uris_with_uuids()) == []


@db_test
def test_assay_upload_merge_extra_metadata(clean_db, monkeypatch):
    """Try to create an assay upload"""
    new_user = Users.create(PROFILE)

    TrialMetadata.create(TRIAL_ID, METADATA)

    assay_upload = UploadJobs.create(
        upload_type="assay_with_extra_md",
        uploader_email=EMAIL,
        gcs_file_map={},
        metadata={
            prism.PROTOCOL_ID_FIELD_NAME: TRIAL_ID,
            "whatever": {
                "hierarchy": [
                    {"we just need a": "uuid-1", "to be able": "to merge"},
                    {"and": "uuid-2"},
                ]
            },
        },
        gcs_xlsx_uri="",
        commit=False,
    )
    assay_upload.id = 111
    clean_db.commit()

    custom_extra_md_parse = MagicMock()
    custom_extra_md_parse.side_effect = lambda f: {"extra": f.read().decode()}
    monkeypatch.setattr(
        "cidc_schemas.prism.merger.EXTRA_METADATA_PARSERS",
        {"assay_with_extra_md": custom_extra_md_parse},
    )

    UploadJobs.merge_extra_metadata(
        111,
        {
            "uuid-1": io.BytesIO(b"within extra md file 1"),
            "uuid-2": io.BytesIO(b"within extra md file 2"),
        },
        session=clean_db,
    )

    assert 1 == clean_db.query(UploadJobs).count()
    au = clean_db.query(UploadJobs).first()
    assert "extra" in au.metadata_patch["whatever"]["hierarchy"][0]
    assert "extra" in au.metadata_patch["whatever"]["hierarchy"][1]


@db_test
def test_assay_upload_ingestion_success(clean_db, monkeypatch, caplog):
    """Check that the ingestion success method works as expected"""
    caplog.set_level(logging.DEBUG)

    new_user = Users.create(PROFILE)
    trial = TrialMetadata.create(TRIAL_ID, METADATA)
    assay_upload = UploadJobs.create(
        upload_type="ihc",
        uploader_email=EMAIL,
        gcs_file_map={},
        metadata={prism.PROTOCOL_ID_FIELD_NAME: TRIAL_ID},
        gcs_xlsx_uri="",
        commit=False,
    )

    clean_db.commit()

    # Ensure that success can't be declared from a starting state
    with pytest.raises(Exception, match="current status"):
        assay_upload.ingestion_success(trial)

    # Update assay_upload status to simulate a completed but not ingested upload
    assay_upload.status = UploadJobStatus.UPLOAD_COMPLETED.value
    assay_upload.ingestion_success(trial)

    # Check that status was updated and email wasn't sent by default
    db_record = UploadJobs.find_by_id(assay_upload.id)
    assert db_record.status == UploadJobStatus.MERGE_COMPLETED.value
    assert "Would send email with subject '[UPLOAD SUCCESS]" not in caplog.text

    # Check that email gets sent when specified
    assay_upload.ingestion_success(trial, send_email=True)
    assert "Would send email with subject '[UPLOAD SUCCESS]" in caplog.text


@db_test
def test_create_downloadable_file_from_metadata(clean_db, monkeypatch):
    """Try to create a downloadable file from artifact_core metadata"""
    # fake file metadata
    file_metadata = {
        "object_url": "10021/Patient 1/sample 1/aliquot 1/wes_forward.fastq",
        "file_size_bytes": 1,
        "md5_hash": "hash1234",
        "facet_group": "foobar",
        "uploaded_timestamp": datetime.now(),
        "foo": "bar",  # unsupported column - should be filtered
    }
    additional_metadata = {"more": "info"}

    # Mock artifact upload publishing
    publisher = MagicMock()
    monkeypatch.setattr("cidc_api.models.models.publish_artifact_upload", publisher)

    # Create the trial (to avoid violating foreign-key constraint)
    TrialMetadata.create(TRIAL_ID, METADATA)

    # Create files with empty or "null" additional metadata
    for nullish_value in ["null", None, {}]:
        df = DownloadableFiles.create_from_metadata(
            TRIAL_ID, "wes_bam", file_metadata, additional_metadata=nullish_value
        )
        clean_db.refresh(df)
        assert df.additional_metadata == {}

    # Create the file
    DownloadableFiles.create_from_metadata(
        TRIAL_ID, "wes_bam", file_metadata, additional_metadata=additional_metadata
    )

    # Check that we created the file
    new_file = (
        clean_db.query(DownloadableFiles)
        .filter_by(object_url=file_metadata["object_url"])
        .first()
    )
    assert new_file
    del file_metadata["foo"]
    for k in file_metadata.keys():
        assert getattr(new_file, k) == file_metadata[k]
    assert new_file.additional_metadata == additional_metadata

    # Check that no artifact upload event was published
    publisher.assert_not_called()

    # Check that artifact upload publishes
    DownloadableFiles.create_from_metadata(
        TRIAL_ID,
        "wes_bam",
        file_metadata,
        additional_metadata=additional_metadata,
        alert_artifact_upload=True,
    )
    publisher.assert_called_once_with(file_metadata["object_url"])


@db_test
def test_downloadable_files_additional_metadata_default(clean_db):
    TrialMetadata.create(TRIAL_ID, METADATA)
    df = DownloadableFiles(
        trial_id=TRIAL_ID,
        upload_type="wes_bam",
        object_url="10021/Patient 1/sample 1/aliquot 1/wes_forward.fastq",
        file_size_bytes=1,
        facet_group="foobar",
        md5_hash="hash1234",
        uploaded_timestamp=datetime.now(),
    )

    # Check no value passed
    df.insert()
    assert df.additional_metadata == {}

    for nullish_value in [None, "null", {}]:
        df.additional_metadata = nullish_value
        df.update()
        assert df.additional_metadata == {}

    # Non-nullish value doesn't get overridden
    non_nullish_value = {"foo": "bar"}
    df.additional_metadata = non_nullish_value
    df.update()
    assert df.additional_metadata == non_nullish_value


@db_test
def test_create_downloadable_file_from_blob(clean_db, monkeypatch):
    """Try to create a downloadable file from a GCS blob"""
    fake_blob = MagicMock()
    fake_blob.name = "name"
    fake_blob.md5_hash = "12345"
    fake_blob.crc32c = "54321"
    fake_blob.size = 5
    fake_blob.time_created = datetime.now()

    TrialMetadata(
        trial_id="id",
        metadata_json={
            "protocol_identifier": "id",
            "allowed_collection_event_names": [],
            "allowed_cohort_names": [],
            "participants": [],
        },
    ).insert(session=clean_db)
    df = DownloadableFiles.create_from_blob(
        "id", "pbmc", "Shipping Manifest", "pbmc/shipping", fake_blob
    )

    # Mock artifact upload publishing
    publisher = MagicMock()
    monkeypatch.setattr("cidc_api.models.models.publish_artifact_upload", publisher)

    # Check that the file was created
    assert 1 == clean_db.query(DownloadableFiles).count()
    df_lookup = DownloadableFiles.find_by_id(df.id)
    assert df_lookup.object_url == fake_blob.name
    assert df_lookup.data_format == "Shipping Manifest"
    assert df_lookup.file_size_bytes == fake_blob.size
    assert df_lookup.md5_hash == fake_blob.md5_hash
    assert df_lookup.crc32c_hash == fake_blob.crc32c

    # uploading second time to check non duplicating entries
    fake_blob.size = 6
    fake_blob.md5_hash = "6"
    df = DownloadableFiles.create_from_blob(
        "id", "pbmc", "Shipping Manifest", "pbmc/shipping", fake_blob
    )

    # Check that the file was created
    assert 1 == clean_db.query(DownloadableFiles).count()
    df_lookup = DownloadableFiles.find_by_id(df.id)
    assert df_lookup.file_size_bytes == 6
    assert df_lookup.md5_hash == "6"

    # Check that no artifact upload event was published
    publisher.assert_not_called()

    # Check that artifact upload publishes
    DownloadableFiles.create_from_blob(
        "id",
        "pbmc",
        "Shipping Manifest",
        "pbmc/shipping",
        fake_blob,
        alert_artifact_upload=True,
    )
    publisher.assert_called_once_with(fake_blob.name)


def test_downloadable_files_data_category_prefix():
    """Check that data_category_prefix's are derived as expected"""
    file_w_category = DownloadableFiles(facet_group="/wes/r1_L.fastq.gz")
    assert file_w_category.data_category_prefix == "WES"

    file_no_category = DownloadableFiles()
    assert file_no_category.data_category_prefix == None


@db_test
def test_downloadable_files_get_related_files(clean_db, cidc_api):
    # Create a trial to avoid constraint errors
    TrialMetadata.create(trial_id=TRIAL_ID, metadata_json=METADATA)

    # Convenience function for building file records
    def create_df(facet_group, additional_metadata={}) -> DownloadableFiles:
        df = DownloadableFiles(
            facet_group=facet_group,
            additional_metadata=additional_metadata,
            trial_id=TRIAL_ID,
            uploaded_timestamp=datetime.now(),
            file_size_bytes=0,
            object_url=facet_group,  # just filler, not relevant to the test
            upload_type="",
        )
        df.insert()
        clean_db.refresh(df)
        return df

    # Set up test data
    cimac_id_1 = "CTTTPPP01.01"
    cimac_id_2 = "CTTTPPP02.01"
    files = [
        create_df(
            "/cytof/normalized_and_debarcoded.fcs", {"some.path.cimac_id": cimac_id_1}
        ),
        create_df(
            "/cytof_analysis/assignment.csv",
            # NOTE: this isn't realistic - assignment files aren't sample-specific - but
            # it serves the purpose of the test.
            {"path.cimac_id": cimac_id_1, "another.path.cimac_id": cimac_id_1},
        ),
        create_df("/cytof_analysis/source.fcs", {"path.to.cimac_id": cimac_id_2}),
        create_df("/cytof_analysis/reports.zip"),
        create_df("/cytof_analysis/analysis.zip"),
        create_df("/wes/r1_L.fastq.gz"),
    ]

    # Based on setup, we expect the following disjoint sets of related files:
    related_file_groups = [
        [files[0], files[1]],
        [files[2]],
        [files[3], files[4]],
        [files[5]],
    ]

    # Check that get_related_files returns what we expect
    with cidc_api.app_context():
        for file_group in related_file_groups:
            for file_record in file_group:
                other_ids = [f.id for f in file_group if f.id != file_record.id]
                related_files = file_record.get_related_files()
                assert set([f.id for f in related_files]) == set(other_ids)
                assert len(related_files) == len(other_ids)


def test_with_default_session(cidc_api, clean_db):
    """Test that the with_default_session decorator provides defaults as expected"""

    @with_default_session
    def check_default_session(expected_session_value, session=None):
        assert session == expected_session_value

    with cidc_api.app_context():
        check_default_session(clean_db)
        fake_session = "some other db session"
        check_default_session(fake_session, session=fake_session)


def test_assay_upload_status():
    """Test UploadJobStatus transition validation logic"""
    upload_statuses = [
        UploadJobStatus.UPLOAD_COMPLETED.value,
        UploadJobStatus.UPLOAD_FAILED.value,
    ]
    merge_statuses = [
        UploadJobStatus.MERGE_COMPLETED.value,
        UploadJobStatus.MERGE_FAILED.value,
    ]
    for upload in upload_statuses:
        assert UploadJobStatus.is_valid_transition(UploadJobStatus.STARTED, upload)
        for merge in merge_statuses:
            assert not UploadJobStatus.is_valid_transition(
                UploadJobStatus.STARTED, merge
            )
            for status in [upload, merge]:
                assert not UploadJobStatus.is_valid_transition(
                    status, UploadJobStatus.STARTED
                )
            assert UploadJobStatus.is_valid_transition(upload, merge)
            assert not UploadJobStatus.is_valid_transition(merge, upload)


@db_test
def test_permissions_insert(clean_db, monkeypatch, caplog):
    gcloud_client = mock_gcloud_client(monkeypatch)
    user = Users(email="test@user.com")
    user.insert()
    trial = TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA)
    trial.insert()

    _insert = MagicMock()
    monkeypatch.setattr(CommonColumns, "insert", _insert)

    # if upload_type is invalid
    with pytest.raises(ValueError, match="invalid upload type"):
        Permissions(upload_type="foo", granted_to_user=user.id, trial_id=trial.trial_id)

    # if don't give granted_by_user
    perm = Permissions(
        granted_to_user=user.id, trial_id=trial.trial_id, upload_type="wes_bam"
    )
    with pytest.raises(IntegrityError, match="`granted_by_user` user must be given"):
        perm.insert()
    _insert.assert_not_called()

    # if give bad granted_by_user
    _insert.reset_mock()
    perm = Permissions(
        granted_to_user=user.id,
        trial_id=trial.trial_id,
        upload_type="wes_bam",
        granted_by_user=999999,
    )
    with pytest.raises(IntegrityError, match="`granted_by_user` user must exist"):
        perm.insert()
    _insert.assert_not_called()

    # if give bad granted_to_user
    _insert.reset_mock()
    perm = Permissions(
        granted_to_user=999999,
        trial_id=trial.trial_id,
        upload_type="wes_bam",
        granted_by_user=user.id,
    )
    with pytest.raises(IntegrityError, match="`granted_to_user` user must exist"):
        perm.insert()
    _insert.assert_not_called()

    # This one will work
    _insert.reset_mock()
    perm = Permissions(
        granted_to_user=user.id,
        trial_id=trial.trial_id,
        upload_type="wes_bam",
        granted_by_user=user.id,
    )
    with caplog.at_level(logging.DEBUG):
        perm.insert()
    _insert.assert_called_once()
    assert any(
        log_record.message.strip()
        == f"admin-action: {user.email} gave {user.email} the permission wes_bam on {trial.trial_id}"
        for log_record in caplog.records
    )
    gcloud_client.grant_lister_access.assert_called_once()
    gcloud_client.grant_download_access.assert_called_once()

    # If granting a permission to a "network-viewer", no GCS IAM actions are taken
    _insert.reset_mock()
    gcloud_client.reset_mocks()
    user.role = CIDCRole.NETWORK_VIEWER.value
    user.update()
    perm = Permissions(
        granted_to_user=user.id,
        trial_id=trial.trial_id,
        upload_type="ihc",
        granted_by_user=user.id,
    )
    perm.insert()
    _insert.assert_called_once()
    gcloud_client.grant_lister_access.assert_not_called()
    gcloud_client.grant_download_access.assert_not_called()

    # If granting a permission to a "pact-user", no GCS IAM actions are taken
    _insert.reset_mock()
    gcloud_client.reset_mocks()
    user.role = CIDCRole.PACT_USER.value
    user.update()
    perm = Permissions(
        granted_to_user=user.id,
        trial_id=trial.trial_id,
        upload_type="ihc",
        granted_by_user=user.id,
    )
    perm.insert()
    _insert.assert_called_once()
    gcloud_client.grant_lister_access.assert_not_called()
    gcloud_client.grant_download_access.assert_not_called()


@db_test
def test_permissions_broad_perms(clean_db, monkeypatch):
    gcloud_client = mock_gcloud_client(monkeypatch)
    user = Users(email="test@user.com")
    user.insert()
    user2 = Users(email="foo@bar.com")
    user2.insert()
    user3 = Users(email="disabled", disabled=True)
    user3.insert()
    trial = TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA)
    trial.insert()
    other_trial = TrialMetadata(
        trial_id="other-trial",
        metadata_json={**METADATA, "protocol_identifier": "other-trial"},
    )
    other_trial.insert()
    for ut in ["wes_fastq", "olink"]:
        for tid in [trial.trial_id, other_trial.trial_id]:
            Permissions(
                granted_to_user=user.id,
                trial_id=tid,
                upload_type=ut,
                granted_by_user=user.id,
            ).insert()

    # Can't insert a permission for access to all trials and assays
    with pytest.raises(ValueError, match="must have a trial id or upload type"):
        Permissions(granted_to_user=user.id, granted_by_user=user.id).insert()

    # Inserting a trial-level permission should delete other more specific related perms.
    trial_query = clean_db.query(Permissions).filter(
        Permissions.trial_id == trial.trial_id
    )
    assert trial_query.count() == 2
    Permissions(
        trial_id=trial.trial_id, granted_to_user=user.id, granted_by_user=user.id
    ).insert()
    assert trial_query.count() == 1
    perm = trial_query.one()
    assert perm.trial_id == trial.trial_id
    assert perm.upload_type is None

    # Inserting an upload-level permission should delete other more specific related perms.
    olink_query = clean_db.query(Permissions).filter(Permissions.upload_type == "olink")
    assert olink_query.count() == 1
    assert olink_query.one().trial_id == other_trial.trial_id
    Permissions(
        upload_type="olink", granted_to_user=user.id, granted_by_user=user.id
    ).insert()
    assert olink_query.count() == 1
    perm = olink_query.one()
    assert perm.trial_id is None
    assert perm.upload_type == "olink"

    # Getting perms for a particular user-trial-type returns broader perms
    perm = Permissions.find_for_user_trial_type(user.id, trial.trial_id, "ihc")
    assert perm is not None and perm.upload_type is None
    perm = Permissions.find_for_user_trial_type(user.id, "some random trial", "olink")
    assert perm is not None and perm.trial_id is None
    del perm  # to prevent mis-pointing

    # Getting all users for a particular user-type returns broader perms
    # insert permission for second user to make sure returns list correctly
    Permissions(
        granted_to_user=user2.id,
        trial_id=None,
        upload_type="olink",
        granted_by_user=user.id,
    ).insert()
    perm_list = Permissions.get_for_trial_type(trial.trial_id, "ihc")
    assert (
        len(perm_list) == 1
        and perm_list[0].upload_type is None
        and perm_list[0].granted_to_user == user.id
    )
    perm_list = Permissions.get_for_trial_type("some random trial", "olink")
    print([p.granted_to_user == user.id for p in perm_list])
    assert len(perm_list) == 2 and all(perm.trial_id is None for perm in perm_list)
    assert all(
        any(perm.granted_to_user == user for perm in perm_list)
        for user in [user.id, user2.id]
    )

    # test that we can return the user emails as well
    # insert permission for second user on other_trial / ihc to make sure returns lists correctly
    Permissions(
        granted_to_user=user2.id,
        trial_id=other_trial.trial_id,
        upload_type="ihc",
        granted_by_user=user.id,
    ).insert()
    # insert permissions for third user who is disabled; should never be returned
    Permissions(
        granted_to_user=user3.id,
        trial_id=other_trial.trial_id,
        upload_type="ihc",
        granted_by_user=user.id,
    ).insert()
    user_email_dict = Permissions.get_user_emails_for_trial_upload(None, None)
    user_email_dict[None]["olink"] = sorted(user_email_dict[None]["olink"])
    assert user_email_dict == {
        None: {"olink": sorted([user.email, user2.email])},
        trial.trial_id: {None: [user.email]},
        other_trial.trial_id: {"ihc": [user2.email], "wes_fastq": [user.email]},
    }

    user_email_dict = Permissions.get_user_emails_for_trial_upload(None, "ihc")
    assert user_email_dict == {
        trial.trial_id: {None: [user.email]},
        other_trial.trial_id: {"ihc": [user2.email]},
    }

    user_email_dict = Permissions.get_user_emails_for_trial_upload(
        trial.trial_id, "ihc"
    )
    assert user_email_dict == {
        trial.trial_id: {None: [user.email]},
    }

    user_email_dict = Permissions.get_user_emails_for_trial_upload(
        "some random trial", "olink"
    )
    user_email_dict[None]["olink"] = sorted(user_email_dict[None]["olink"])
    assert user_email_dict == {
        None: {"olink": sorted([user.email, user2.email])},
    }

    user_email_dict = Permissions.get_user_emails_for_trial_upload(
        other_trial.trial_id, None
    )
    user_email_dict[None]["olink"] = sorted(user_email_dict[None]["olink"])
    assert user_email_dict == {
        None: {"olink": sorted([user.email, user2.email])},
        other_trial.trial_id: {"ihc": [user2.email], "wes_fastq": [user.email]},
    }

    # when it's the only one in a request, doesn't return anything
    Permissions(
        granted_to_user=user3.id,
        trial_id=other_trial.trial_id,
        upload_type="hande",
        granted_by_user=user.id,
    ).insert()
    assert (
        Permissions.get_user_emails_for_trial_upload(other_trial.trial_id, "hande")
        == {}
    )
    # when there's other things in the trial, still returns the trial
    user_email_dict = Permissions.get_user_emails_for_trial_upload(
        other_trial.trial_id, None
    )
    user_email_dict[None]["olink"] = sorted(user_email_dict[None]["olink"])
    assert user_email_dict == {
        None: {"olink": sorted([user.email, user2.email])},
        other_trial.trial_id: {"ihc": [user2.email], "wes_fastq": [user.email]},
    }
    # when there's something else in the same assay, still doesn't the disabled one
    Permissions(
        granted_to_user=user2.id,
        trial_id=trial.trial_id,
        upload_type="hande",
        granted_by_user=user.id,
    ).insert()
    user_email_dict = Permissions.get_user_emails_for_trial_upload(None, "hande")
    assert user_email_dict == {
        trial.trial_id: {None: [user.email], "hande": [user2.email]}
    }


@db_test
def test_permissions_delete(clean_db, monkeypatch, caplog):
    gcloud_client = mock_gcloud_client(monkeypatch)
    user = Users(email="test@user.com")
    user.insert()
    trial = TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA)
    trial.insert()
    perm = Permissions(
        granted_to_user=user.id,
        trial_id=trial.trial_id,
        upload_type="wes_bam",
        granted_by_user=user.id,
    )
    perm.insert()

    # Deleting a record by a user doesn't exist leads to an error
    gcloud_client.reset_mocks()
    with pytest.raises(NoResultFound, match="no user with id"):
        perm.delete(deleted_by=999999)

    # Deletion of an existing permission leads to no error
    gcloud_client.reset_mocks()
    with caplog.at_level(logging.DEBUG):
        perm.delete(deleted_by=user.id)
    gcloud_client.revoke_lister_access.assert_called_once()
    gcloud_client.revoke_download_access.assert_called_once()
    gcloud_client.grant_lister_access.assert_not_called()
    gcloud_client.grant_download_access.assert_not_called()
    assert any(
        log_record.message.strip()
        == f"admin-action: {user.email} removed from {user.email} the permission wes_bam on {trial.trial_id}"
        for log_record in caplog.records
    )

    # Deleting an already-deleted record is idempotent
    gcloud_client.reset_mocks()
    perm.delete(deleted_by=user)
    gcloud_client.revoke_lister_access.assert_called_once()
    gcloud_client.revoke_download_access.assert_called_once()
    gcloud_client.grant_download_access.assert_not_called()
    gcloud_client.grant_lister_access.assert_not_called()

    # Deleting a record whose user doesn't exist leads to an error
    gcloud_client.reset_mocks()
    with pytest.raises(NoResultFound, match="no user with id"):
        Permissions(granted_to_user=999999).delete(deleted_by=user)

    gcloud_client.revoke_lister_access.assert_not_called()
    gcloud_client.grant_lister_access.assert_not_called()
    gcloud_client.revoke_download_access.assert_not_called()
    gcloud_client.grant_download_access.assert_not_called()

    # If revoking a permission from a "network-viewer", no GCS IAM actions are taken
    gcloud_client.reset_mocks()
    user.role = CIDCRole.NETWORK_VIEWER.value
    user.update()
    perm = Permissions(
        granted_to_user=user.id,
        trial_id=trial.trial_id,
        upload_type="ihc",
        granted_by_user=user.id,
    )
    perm.insert()
    perm.delete(deleted_by=user)
    gcloud_client.revoke_lister_access.assert_not_called()
    gcloud_client.revoke_download_access.assert_not_called()

    # If revoking a permission from a "pact-user", no GCS IAM actions are taken
    gcloud_client.reset_mocks()
    user.role = CIDCRole.PACT_USER.value
    user.update()
    perm = Permissions(
        granted_to_user=user.id,
        trial_id=trial.trial_id,
        upload_type="ihc",
        granted_by_user=user.id,
    )
    perm.insert()
    perm.delete(deleted_by=user)
    gcloud_client.revoke_lister_access.assert_not_called()
    gcloud_client.revoke_download_access.assert_not_called()


@db_test
def test_permissions_grant_user_permissions(clean_db, monkeypatch):
    """
    Smoke test that Permissions.grant_user_permissions calls grant_download_access with the right arguments.
    """
    refresh_intake_access = MagicMock()
    monkeypatch.setattr(
        "cidc_api.models.models.refresh_intake_access", refresh_intake_access
    )

    gcloud_client = mock_gcloud_client(monkeypatch)
    user, user2 = (
        Users(email="test@user.com", role=CIDCRole.NETWORK_VIEWER.value),
        Users(email="foo@bar.com"),
    )
    user.insert(), user2.insert()
    trial = TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA)
    trial.insert()

    upload_types = ["wes_bam", "ihc", "rna_fastq", "plasma"]
    for upload_type in upload_types:
        Permissions(
            granted_to_user=user.id,
            trial_id=trial.trial_id,
            upload_type=upload_type,
            granted_by_user=user.id,
        ).insert()
    Permissions(
        granted_to_user=user2.id,
        trial_id=trial.trial_id,
        upload_type="ihc",
        granted_by_user=user.id,
    )

    # IAM permissions not granted to network viewers
    Permissions.grant_user_permissions(user=user)
    gcloud_client.grant_lister_access.assert_not_called()
    gcloud_client.grant_download_access.assert_not_called()

    # IAM permissions still not granted to pact users
    user.role = CIDCRole.PACT_USER.value
    Permissions.grant_user_permissions(user=user)
    gcloud_client.grant_lister_access.assert_not_called()
    gcloud_client.grant_download_access.assert_not_called()

    # IAM permissions should be granted for any other role
    user.role = CIDCRole.CIMAC_USER.value
    Permissions.grant_user_permissions(user=user)
    gcloud_client.grant_lister_access.assert_called_once_with(user.email)
    gcloud_client.grant_download_access.assert_has_calls(
        [
            call(
                user.email,
                trial.trial_id,
                upload_type,
            )
            for upload_type in upload_types
        ],
        any_order=True,
    )

    refresh_intake_access.assert_called_once_with(user.email)


@db_test
def test_permissions_grant_download_permissions_for_upload_job(clean_db, monkeypatch):
    """
    Smoke test that Permissions.grant_download_permissions_for_upload_job calls grant_download_access with the right arguments.
    """
    #  copied from
    gcloud_client = mock_gcloud_client(monkeypatch)
    trial = TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA)
    trial2_metadata = deepcopy(METADATA)
    trial2_metadata[prism.PROTOCOL_ID_FIELD_NAME] += "2"
    trial2 = TrialMetadata(
        trial_id=trial2_metadata[prism.PROTOCOL_ID_FIELD_NAME], metadata_json=METADATA
    )
    user1 = Users(email="test@user.com")
    user2 = Users(email="test2@user.com")
    user3 = Users(email="test3@user.com")

    trial.insert(), trial2.insert()
    user1.insert(), user2.insert(), user3.insert()

    # Set up UploadJobs for testing: status to simulate a completed but not ingested upload
    upload_trial_ihc = UploadJobs.create(
        upload_type="ihc",
        uploader_email=user1.email,
        gcs_file_map={},
        metadata={prism.PROTOCOL_ID_FIELD_NAME: trial.trial_id},
        gcs_xlsx_uri="",
        commit=False,
    )
    upload_trial_ihc.status = UploadJobStatus.UPLOAD_COMPLETED.value
    upload_trial_ihc.ingestion_success(trial)

    upload_trial_wes = UploadJobs.create(
        upload_type="wes_bam",
        uploader_email=user1.email,
        gcs_file_map={},
        metadata={prism.PROTOCOL_ID_FIELD_NAME: trial.trial_id},
        gcs_xlsx_uri="",
        commit=False,
    )
    upload_trial_wes.status = UploadJobStatus.UPLOAD_COMPLETED.value
    upload_trial_wes.ingestion_success(trial)

    upload_trial2_wes = UploadJobs.create(
        upload_type="wes_bam",
        uploader_email=user1.email,
        gcs_file_map={},
        metadata={prism.PROTOCOL_ID_FIELD_NAME: trial2.trial_id},
        gcs_xlsx_uri="",
        commit=False,
    )
    upload_trial2_wes.status = UploadJobStatus.UPLOAD_COMPLETED.value
    upload_trial2_wes.ingestion_success(trial2)

    upload_trial2_rna = UploadJobs.create(
        upload_type="rna_fastq",
        uploader_email=user1.email,
        gcs_file_map={},
        metadata={prism.PROTOCOL_ID_FIELD_NAME: trial2.trial_id},
        gcs_xlsx_uri="",
        commit=False,
    )
    upload_trial2_rna.status = UploadJobStatus.UPLOAD_COMPLETED.value
    upload_trial2_rna.ingestion_success(trial2)

    upload_trial_clinical = UploadJobs.create(
        upload_type="clinical_data",
        uploader_email=user1.email,
        gcs_file_map={},
        metadata={prism.PROTOCOL_ID_FIELD_NAME: trial.trial_id},
        gcs_xlsx_uri="",
        commit=False,
    )
    upload_trial_clinical.status = UploadJobStatus.UPLOAD_COMPLETED.value
    upload_trial_clinical.ingestion_success(trial)

    # Test uploads:
    #   trial ihc
    #   trial clinical_data
    # Permissions to add:
    #   user1: trial/wes_bam, trial/ihc, trial/rna, trial/plasma, trial/clinical_data]
    #   user2: */ihc, trial2/wes_bam, trial2/rna_fastq
    #   user3: trial/*, */wes_bam
    # Tests to run:
    #   trial ihc - single, cross-trial, cross-assay
    #       user1 (trial/ihc), user2 (*/ihc), user3 (trial/*)
    #   trial wes_bam - single, cross-assay, NO cross-trial
    #       user1 (trial/wes_bam), user3 (trial/*)
    #   trial2 wes_bam - single, cross-trial, NO cross-assay
    #       user2 (trial/wes_bam), user3 (*/wes_bam)
    #   trial2 rna_fastq - single assay, NO cross-assay, NO cross-trial
    #       user2 (trial2/rna)
    #   trial clinical_data - single clinical_data, NO cross-assay, NO cross-trial
    #       user1 (trial/clinical_data)
    upload_types = ["wes_bam", "ihc", "rna_fastq", "plasma", "clinical_data"]
    for upload_type in upload_types:
        Permissions(
            granted_to_user=user1.id,
            trial_id=trial.trial_id,
            upload_type=upload_type,
            granted_by_user=user1.id,
        ).insert()

    Permissions(
        granted_to_user=user2.id,
        trial_id=None,
        upload_type=upload_trial_ihc.upload_type,
        granted_by_user=user1.id,
    ).insert()
    upload_types = ["wes_bam", "rna_fastq"]
    for upload_type in upload_types:
        Permissions(
            granted_to_user=user2.id,
            trial_id=trial2.trial_id,
            upload_type=upload_type,
            granted_by_user=user1.id,
        ).insert()

    Permissions(
        granted_to_user=user3.id,
        trial_id=trial.trial_id,
        upload_type=None,
        granted_by_user=user1.id,
    ).insert()
    Permissions(
        granted_to_user=user3.id,
        trial_id=None,
        upload_type="wes_bam",
        granted_by_user=user1.id,
    ).insert()
    clean_db.commit()

    gcloud_client.reset_mocks()
    # trigger and assert
    Permissions.grant_download_permissions_for_upload_job(
        upload_trial_ihc, session=clean_db
    )
    gcloud_client.grant_lister_access.assert_has_calls(
        [call(user1.email), call(user2.email), call(user3.email)]
    )
    gcloud_client.grant_download_access.assert_called_once_with(
        [user1.email, user2.email, user3.email],
        upload_trial_ihc.trial_id,
        upload_trial_ihc.upload_type,
    )

    gcloud_client.reset_mocks()
    # trigger and assert
    Permissions.grant_download_permissions_for_upload_job(
        upload_trial_wes, session=clean_db
    )
    gcloud_client.grant_lister_access.assert_has_calls(
        [call(user1.email), call(user3.email)]
    )
    gcloud_client.grant_download_access.assert_called_once_with(
        [user1.email, user3.email],
        upload_trial_wes.trial_id,
        upload_trial_wes.upload_type,
    )

    gcloud_client.reset_mocks()
    # trigger and assert
    Permissions.grant_download_permissions_for_upload_job(
        upload_trial2_wes, session=clean_db
    )
    gcloud_client.grant_lister_access.assert_has_calls(
        [call(user2.email), call(user3.email)]
    )
    gcloud_client.grant_download_access.assert_called_once_with(
        [user2.email, user3.email],
        upload_trial2_wes.trial_id,
        upload_trial2_wes.upload_type,
    )

    gcloud_client.reset_mocks()
    # trigger and assert
    Permissions.grant_download_permissions_for_upload_job(
        upload_trial2_rna, session=clean_db
    )
    gcloud_client.grant_lister_access.assert_has_calls([call(user2.email)])
    gcloud_client.grant_download_access.assert_called_once_with(
        [user2.email], upload_trial2_rna.trial_id, upload_trial2_rna.upload_type
    )

    gcloud_client.reset_mocks()
    # trigger and assert
    Permissions.grant_download_permissions_for_upload_job(
        upload_trial_clinical, session=clean_db
    )
    gcloud_client.grant_lister_access.assert_has_calls([call(user1.email)])
    gcloud_client.grant_download_access.assert_called_once_with(
        [user1.email], upload_trial_clinical.trial_id, upload_trial_clinical.upload_type
    )


@db_test
def test_permissions_grant_download_permissions(clean_db, monkeypatch):
    """
    Smoke test that Permissions.grant_download_permissions calls grant_download_access with the right arguments.
    """
    gcloud_client = mock_gcloud_client(monkeypatch)
    user = Users(email="test@user.com", role=CIDCRole.CIDC_BIOFX_USER.value)
    user2 = Users(email="foo@bar.com", role=CIDCRole.CIDC_BIOFX_USER.value)
    user.insert(), user2.insert()

    trial2_id = f"{TRIAL_ID}2"
    trial, trial2 = (
        TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA),
        TrialMetadata(trial_id=trial2_id, metadata_json=METADATA),
    )
    trial.insert(), trial2.insert()

    upload_types = ["wes_bam", "rna_fastq", "plasma", "ihc"]
    for upload_type in upload_types:
        Permissions(
            granted_to_user=user.id,
            trial_id=None if upload_type == "ihc" else trial.trial_id,
            upload_type=upload_type,
            granted_by_user=user.id,
        ).insert()
    Permissions(
        granted_to_user=user2.id,
        trial_id=None,
        upload_type="ihc",
        granted_by_user=user.id,
    ).insert()
    Permissions(
        granted_to_user=user2.id,
        trial_id=trial2.trial_id,
        upload_type="plasma",
        granted_by_user=user.id,
    ).insert()

    # all permissions
    gcloud_client.reset_mocks()
    Permissions.grant_download_permissions(None, None)
    gcloud_client.grant_lister_access.assert_has_calls(
        [call(user.email), call(user2.email)]
    )
    assert sorted(gcloud_client.grant_download_access.call_args_list) == sorted(
        [
            call([user.email, user2.email], None, "ihc"),
            call([user2.email], trial2.trial_id, "plasma"),
        ]
        + [
            call([user.email], trial.trial_id, upload_type)
            for upload_type in upload_types
            if upload_type != "ihc"
        ]
    )

    # single trial, cross assay
    gcloud_client.reset_mocks()
    Permissions.grant_download_permissions(trial2.trial_id, None)
    gcloud_client.grant_lister_access.assert_has_calls(
        [call(user.email), call(user2.email)]
    )
    gcloud_client.grant_download_access.assert_has_calls(
        [
            call([user.email, user2.email], trial2.trial_id, "ihc"),
            call([user2.email], trial2.trial_id, "plasma"),
        ]
    )

    # single assay, cross trial
    gcloud_client.reset_mocks()
    Permissions.grant_download_permissions(None, "plasma")
    gcloud_client.grant_lister_access.assert_has_calls(
        [call(user.email), call(user2.email)]
    )
    gcloud_client.grant_download_access.assert_has_calls(
        [
            call([user.email], trial.trial_id, "plasma"),
            call([user2.email], trial2.trial_id, "plasma"),
        ]
    )

    # single assay, single trial
    gcloud_client.reset_mocks()
    Permissions.grant_download_permissions(trial.trial_id, "plasma")
    gcloud_client.grant_lister_access.assert_called_once_with(user.email)
    gcloud_client.grant_download_access.assert_called_once_with(
        [user.email], trial.trial_id, "plasma"
    )

    # not called on admins or nci biobank users
    for role in [CIDCRole.ADMIN.value, CIDCRole.NCI_BIOBANK_USER.value]:
        gcloud_client.reset_mocks()
        user.role = role
        user.update()
        Permissions.grant_download_permissions(None, None)
        gcloud_client.grant_lister_access.assert_called_once_with(user2.email)
        for c in [
            call([user2.email], trial2.trial_id, "plasma"),
            call([user2.email], None, "ihc"),
        ]:
            assert c in gcloud_client.grant_download_access.call_args_list


@db_test
def test_permissions_revoke_download_permissions(clean_db, monkeypatch):
    """
    Smoke test that Permissions.revoke_download_permissions calls revoke_download_access the right arguments.
    """
    gcloud_client = mock_gcloud_client(monkeypatch)
    user = Users(email="test@user.com", role=CIDCRole.CIDC_BIOFX_USER.value)
    user2 = Users(email="foo@bar.com", role=CIDCRole.CIDC_BIOFX_USER.value)
    user.insert(), user2.insert()

    trial2_id = f"{TRIAL_ID}2"
    trial, trial2 = (
        TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA),
        TrialMetadata(trial_id=trial2_id, metadata_json=METADATA),
    )
    trial.insert(), trial2.insert()

    upload_types = ["wes_bam", "ihc", "rna_fastq", "plasma"]
    for upload_type in upload_types:
        Permissions(
            granted_to_user=user.id,
            trial_id=None if upload_type == "ihc" else trial.trial_id,
            upload_type=upload_type,
            granted_by_user=user.id,
        ).insert()
    Permissions(
        granted_to_user=user2.id,
        trial_id=None,
        upload_type="ihc",
        granted_by_user=user.id,
    ).insert()
    Permissions(
        granted_to_user=user2.id,
        trial_id=trial2.trial_id,
        upload_type="plasma",
        granted_by_user=user.id,
    ).insert()

    # all permissions
    gcloud_client.reset_mocks()
    Permissions.revoke_download_permissions(None, None)
    gcloud_client.revoke_lister_access.assert_not_called()
    for c in [
        call([user.email, user2.email], None, "ihc"),
        call([user2.email], trial2.trial_id, "plasma"),
        call([user.email], trial.trial_id, "plasma"),
    ] + [
        call([user.email], trial.trial_id, upload_type)
        for upload_type in upload_types
        if upload_type != "ihc"
    ]:
        assert any(
            test_call == c
            for test_call in gcloud_client.revoke_download_access.call_args_list
        ), str(c)

    # single trial, cross assay
    gcloud_client.reset_mocks()
    Permissions.revoke_download_permissions(trial2.trial_id, None)
    gcloud_client.revoke_lister_access.assert_not_called()
    gcloud_client.revoke_download_access.assert_has_calls(
        [
            call([user.email, user2.email], trial2.trial_id, "ihc"),
            call([user2.email], trial2.trial_id, "plasma"),
        ]
    )

    # single assay, cross trial
    gcloud_client.reset_mocks()
    Permissions.revoke_download_permissions(None, "plasma")
    gcloud_client.revoke_lister_access.assert_not_called()
    gcloud_client.revoke_download_access.assert_has_calls(
        [
            call([user.email], trial.trial_id, "plasma"),
            call([user2.email], trial2.trial_id, "plasma"),
        ]
    )

    # single assay, single trial
    gcloud_client.reset_mocks()
    Permissions.revoke_download_permissions(trial.trial_id, "plasma")
    gcloud_client.revoke_lister_access.assert_not_called()
    gcloud_client.revoke_download_access.assert_called_once_with(
        [user.email], trial.trial_id, "plasma"
    )


@db_test
def test_user_confirm_approval(clean_db, monkeypatch):
    """Ensure that users are notified when their account goes from pending to approved."""
    confirm_account_approval = MagicMock()
    monkeypatch.setattr(
        "cidc_api.shared.emails.confirm_account_approval", confirm_account_approval
    )

    user = Users(email="test@user.com")
    user.insert()

    # The confirmation email shouldn't be sent for updates unrelated to account approval
    user.update(changes={"first_n": "foo"})
    confirm_account_approval.assert_not_called()

    # The confirmation email should be sent for updates related to account approval
    user.update(changes={"approval_date": datetime.now()})
    confirm_account_approval.assert_called_once_with(user, send_email=True)


@db_test
def test_user_get_data_access_report(clean_db, monkeypatch):
    """Test that user data access info is collected as expected"""
    mock_gcloud_client(monkeypatch)

    admin_user = Users(
        email="admin@email.com",
        organization="CIDC",
        approval_date=datetime.now(),
        role=CIDCRole.ADMIN.value,
    )
    admin_user.insert(session=clean_db)

    cimac_user = Users(
        email="cimac@email.com",
        organization="DFCI",
        approval_date=datetime.now(),
        role=CIDCRole.CIMAC_USER.value,
    )
    cimac_user.insert(session=clean_db)

    trial = TrialMetadata(trial_id=TRIAL_ID, metadata_json=METADATA)
    trial.insert(session=clean_db)

    trial2 = TrialMetadata(trial_id=TRIAL_ID + "2", metadata_json=METADATA)
    trial2.insert(session=clean_db)

    upload_types = ["wes_bam", "ihc"]

    # Note that admins don't need permissions to view data,
    # so we're deliberately issuing unnecessary permissions here.
    for user in [admin_user, cimac_user]:
        for t in upload_types:
            Permissions(
                granted_to_user=user.id,
                granted_by_user=admin_user.id,
                trial_id=trial.trial_id,
                upload_type=t,
            ).insert(session=clean_db)

    # Add a clinical_data permission
    Permissions(
        granted_to_user=cimac_user.id,
        granted_by_user=admin_user.id,
        trial_id=trial2.trial_id,
        upload_type="clinical_data",
    ).insert(session=clean_db)

    # Add a cross-assay permission
    # Should NOT affect the clinical_data perm above
    Permissions(
        granted_to_user=cimac_user.id,
        granted_by_user=admin_user.id,
        trial_id=trial2.trial_id,
        upload_type=None,
    ).insert(session=clean_db)

    # Add a cross-trial permission as well
    Permissions(
        granted_to_user=cimac_user.id,
        granted_by_user=admin_user.id,
        trial_id=None,
        upload_type="olink",
    ).insert(session=clean_db)

    bio = io.BytesIO()
    result_df = Users.get_data_access_report(bio, session=clean_db)
    bio.seek(0)

    # Make sure bytes were written to the BytesIO instance
    assert bio.getbuffer().nbytes > 0

    # Make sure report data has expected info
    assert set(result_df.columns) == set(
        ["email", "role", "organization", "trial_id", "permissions"]
    )
    for t in [trial, trial2]:
        trial_df = pd.read_excel(bio, t.trial_id)
        for user in [admin_user, cimac_user]:
            user_df = trial_df[trial_df.email == user.email]
            assert set([user.role]) == set(user_df.role)
            assert set([user.organization]) == set(user_df.organization)
            if user == admin_user:
                #  trial_id    permissions
                # --------------------------
                # {trial_id} *,clinical_data
                assert set(["*,clinical_data"]) == set(user_df.permissions)
            else:  # user == cimac_user
                if t == trial:
                    #  trial_id   permissions
                    # ------------------------
                    # {trial_id} "wes_bam,ihc" < or reverse
                    #      *       "olink"
                    assert len(user_df.index) == 2
                    assert sum(user_df.trial_id == t.trial_id) == 1
                    assert set(
                        user_df.permissions[user_df.trial_id == t.trial_id]
                        .iloc[0]
                        .split(",")
                    ) == set(["ihc", "wes_bam"])
                    assert (
                        user_df.permissions[user_df.trial_id != t.trial_id] == "olink"
                    ).all()
                else:  # t == trial2
                    #  trial_id    permissions
                    # --------------------------
                    # {trial_id} clinical_data,* < or reverse
                    #      *         "olink"
                    assert len(user_df.index) == 2
                    assert sum(user_df.trial_id == t.trial_id) == 1
                    assert set(
                        user_df.permissions[user_df.trial_id == t.trial_id]
                        .iloc[0]
                        .split(",")
                    ) == set(["*", "clinical_data"])
                    assert (
                        user_df.permissions[user_df.trial_id != t.trial_id] == "olink"
                    ).all()
