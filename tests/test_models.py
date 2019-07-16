from functools import wraps

import pytest

from app import app
from models import Users, TrialMetadata, UploadJobs

from .util import assert_same_elements


@pytest.fixture
def db():
    """Provide a clean test database session"""
    session = app.data.driver.session
    session.query(Users).delete()
    session.query(TrialMetadata).delete()
    session.commit()

    return session


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


@db_test
def test_create_user(db):
    """Try to create a user that doesn't exist"""
    Users.create(EMAIL)
    user = db.query(Users).filter_by(email=EMAIL).first()
    assert user
    assert user.email == EMAIL


@db_test
def test_duplicate_user(db):
    """Ensure that a user won't be created twice"""
    Users.create(EMAIL)
    Users.create(EMAIL)
    assert db.query(Users).count() == 1


TRIAL_ID = "cimac-12345"
METADATA = {"foo": {"bar": "baz"}}


@db_test
def test_create_trial_metadata(db):
    """Insert a trial metadata record if one doesn't exist"""
    TrialMetadata.patch_trial_metadata(TRIAL_ID, METADATA)
    trial = db.query(TrialMetadata).filter_by(trial_id=TRIAL_ID).first()
    assert trial
    assert trial.metadata_json == METADATA


@db_test
def test_update_trial_metadata(db):
    """Update an existing trial_metadata_record"""
    TrialMetadata.patch_trial_metadata(TRIAL_ID, METADATA)

    updated_metadata = METADATA.update({"fiz": "buzz"})

    with pytest.raises(NotImplementedError, match="updates not yet supported"):
        TrialMetadata.patch_trial_metadata(TRIAL_ID, updated_metadata)


@db_test
def test_create_upload_job(db):
    """Try to create an upload job"""
    gcs_objects = ["my/first/wes/blob1", "my/first/wes/blob2"]
    metadata_json_patch = {"foo": "bar"}
    xlsx_bytes = b"1234"

    create_job = lambda: UploadJobs.create(gcs_objects, metadata_json_patch, xlsx_bytes)

    # Create a fresh upload job
    new_job = create_job()
    job = db.query(UploadJobs).filter_by(id=new_job.id).first()
    assert_same_elements(new_job.gcs_objects, job.gcs_objects)
    assert job.status == "started"

    # Try to re-create that same job, ensuring the existing job is returned
    same_job = create_job()
    assert same_job.id == new_job.id
