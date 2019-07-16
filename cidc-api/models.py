from typing import BinaryIO

from flask import current_app as app
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    VARCHAR,
    Enum,
    Index,
    func,
    and_,
    cast,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, BYTEA
from sqlalchemy.ext.declarative import declarative_base

BaseModel = declarative_base()


class CommonColumns(BaseModel):
    """Metadata attributes that Eve uses on all resources"""

    __abstract__ = True  # Indicate that this isn't a Table schema

    _created = Column(DateTime, default=func.now())
    _updated = Column(DateTime, default=func.now(), onupdate=func.now())
    _etag = Column(String(40))


ORGS = ["CIDC", "DFCI", "ICAHN", "STANFORD", "ANDERSON"]


class Users(CommonColumns):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    first_n = Column(String)
    last_n = Column(String)
    organization = Column(Enum(*ORGS, name="orgs"))

    @staticmethod
    def create(email: str):
        """
            Create a new record for a user if one doesn't exist
            for the given email. Return the user record associated
            with that email.
        """
        session = app.data.driver.session
        user = session.query(Users).filter_by(email=email).first()
        if not user:
            app.logger.info(f"Creating new user with email {email}")
            user = Users(email=email)
            session.add(user)
            session.commit()
        return user


class TrialMetadata(CommonColumns):
    __tablename__ = "trial_metadata"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    # The CIMAC-determined trial id
    trial_id = Column(String, unique=True, nullable=False, index=True)
    metadata_json = Column(JSONB, nullable=False)

    # Create a GIN index on the metadata JSON blobs
    _metadata_idx = Index("metadata_idx", metadata_json, postgresql_using="gin")

    @staticmethod
    def patch_trial_metadata(trial_id: str, metadata: dict):
        """
            Applies updates to an existing trial metadata record,
            or create a new one if it does not exist.

            Args:
                trial_id: the lead organization study id for this trial
                metadata: a partial metadata object for trial_id

            TODO: implement metadata merging, either here or in cidc_schemas
        """
        session = app.data.driver.session

        # Look for an existing trial
        trial = session.query(TrialMetadata).filter_by(trial_id=trial_id).first()

        if trial:
            # Merge-update metadata into existing trial's metadata_json
            raise NotImplementedError("metadata updates not yet supported")
        else:
            # Create a new trial metadata record, since none exists
            app.logger.info(f"Creating new trial_metadata for trial {trial_id}")
            new_trial = TrialMetadata(trial_id=trial_id, metadata_json=metadata)
            session.add(new_trial)
            session.commit()


STATUSES = ["started", "completed", "errored"]


class UploadJobs(CommonColumns):
    __tablename__ = "upload_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    # The current status of the upload job
    status = Column(Enum(*STATUSES, name="job_statuses"), nullable=False)
    # The object names for the files to be uploaded
    gcs_objects = Column(ARRAY(String, dimensions=1), nullable=False)
    # The parsed JSON metadata blob associated with this upload
    metadata_json_patch = Column(JSONB, nullable=False)
    # The contents of the xlsx metadata file, if available
    xlsx_bytes = Column(BYTEA)

    # Create a GIN index on the GCS object names
    _gcs_objects_idx = Index("gcs_objects_idx", gcs_objects, postgresql_using="gin")

    @staticmethod
    def _has_same_gcs_objects(gcs_objects: list):
        # By some SQLAlchemy weirdness, this typecast is required
        # for the Array comparators to work.
        varchar_objs = cast(gcs_objects, ARRAY(VARCHAR()))
        return and_(
            UploadJobs.gcs_objects.contains(varchar_objs),
            UploadJobs.gcs_objects.contained_by(varchar_objs),
        )

    @staticmethod
    def create(gcs_objects: list, metadata: dict, xlsx_bytes: BinaryIO):
        """Create a new upload job for the given trial metadata patch."""
        session = app.data.driver.session

        # Look for an existing upload job for these objects
        job = (
            session.query(UploadJobs)
            .filter(UploadJobs._has_same_gcs_objects(gcs_objects))
            .first()
        )

        if job:
            # TODO: what to do if these files are already on the way to being uploaded?
            pass
        else:
            # Create a new one if none exists
            job = UploadJobs(
                gcs_objects=gcs_objects,
                metadata_json_patch=metadata,
                xlsx_bytes=xlsx_bytes,
                status="started",
            )
            session.add(job)
            session.commit()

        return job

