from functools import wraps
from typing import Optional

from marshmallow import fields
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


class _ListMetadata(BaseSchema):
    total = fields.Int(required=True)
    # TODO: do we need these fields?
    # page_num = fields.Int(required=True)
    # page_size = fields.Int(required=True)


def _make_list_schema(schema: BaseSchema):
    class ListSchema(BaseSchema):
        _items = fields.List(fields.Nested(schema), required=True)
        _meta = fields.Nested(_ListMetadata(), required=True)

    return ListSchema


class UploadJobSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = UploadJobs


UploadJobListSchema = _make_list_schema(UploadJobSchema())


class UserSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Users


UserListSchema = _make_list_schema(UserSchema())


class DownloadableFileSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = DownloadableFiles


DownloadableFileListSchema = _make_list_schema(DownloadableFileSchema())


class PermissionSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Permissions


PermissionListSchema = _make_list_schema(PermissionSchema())


class TrialMetadataSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = TrialMetadata


TrialMetadataListSchema = _make_list_schema(TrialMetadataSchema())
