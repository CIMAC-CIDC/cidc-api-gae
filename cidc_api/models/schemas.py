from functools import wraps
from typing import Optional

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from ..config.db import db
from .models import (
    BaseModel,
    UploadJobs,
    Users,
    DownloadableFiles,
    Permissions,
    TrialMetadata,
)


class BaseSchema(SQLAlchemyAutoSchema):
    class Meta:
        sqla_session = db.session
        include_fk = True
        load_instance = True


class UploadJobSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = UploadJobs


class UserSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Users


class DownloadableFileSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = DownloadableFiles


class PermissionSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Permissions


class TrialMetadataSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = TrialMetadata
