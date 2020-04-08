from typing import List

from flask import Blueprint, jsonify
from webargs import fields
from webargs.flaskparser import use_args
from werkzeug.exceptions import NotFound


from ..models import CIDCRole, DownloadableFiles, DownloadableFileSchema, Permissions
from ..shared import gcloud_client
from ..shared.auth import get_current_user, requires_auth
from ..shared.rest_utils import (
    lookup,
    marshal_response,
    unmarshal_request,
    use_args_with_pagination,
)

downloadable_files_bp = Blueprint("downloadable_files", __name__)

downloadable_files_schema = DownloadableFileSchema()
downloadable_files_list_schema = DownloadableFileSchema(many=True)


file_filter_params = {
    "trial_ids": fields.DelimitedList(fields.Str(), default=[]),
    "upload_types": fields.DelimitedList(fields.Str(), default=[]),
}


@downloadable_files_bp.route("/", methods=["GET"])
@requires_auth("downloadable_files")
@use_args_with_pagination(file_filter_params, downloadable_files_schema)
@marshal_response(downloadable_files_list_schema)
def list_downloadable_files(args, pagination_args) -> List[DownloadableFiles]:
    """List downloadable files that the current user is allowed to view."""
    user = get_current_user()

    # Admins can view all files
    if user.is_admin():
        return DownloadableFiles.list(**args, **pagination_args)

    return DownloadableFiles.list_for_user(user.id, **args, **pagination_args)


@downloadable_files_bp.route("/<int:downloadable_file>", methods=["GET"])
@requires_auth("downloadable_files")
@lookup(DownloadableFiles, "downloadable_file")
@marshal_response(downloadable_files_schema)
def get_downloadable_file(downloadable_file: DownloadableFiles) -> DownloadableFiles:
    """Get a single file by ID if the current user is allowed to view it."""
    user = get_current_user()

    # Admins can view any file
    if user.is_admin():
        return downloadable_file

    # Check that a non-admin has permission to view this file
    perm = Permissions.find_for_user_trial_type(
        user.id, downloadable_file.trial_id, downloadable_file.upload_type
    )

    if not perm:
        raise NotFound()

    return downloadable_file


@downloadable_files_bp.route("/download_url", methods=["GET"])
@requires_auth("download_url")
@use_args({"id": fields.Str(required=True)}, location="query")
def get_download_url(args):
    """
    Get a signed GCS download URL for a given file.
    """
    # Extract file ID from route
    file_id = args["id"]

    # Check that file exists
    file_record = DownloadableFiles.find_by_id(file_id)
    if not file_record:
        raise NotFound(f"No file with id {file_id}.")

    user = get_current_user()

    # Ensure user has permission to access this file
    perms = Permissions.find_for_user(user.id)
    if user.role != CIDCRole.ADMIN.value:
        # Check for a permission matching this file's trial and assay
        if not any(
            perm.upload_type == file_record.upload_type
            and perm.trial_id == file_record.trial_id
            for perm in perms
        ):
            raise NotFound(f"No file with id {file_id}.")

    # Generate the signed URL and return it.
    download_url = gcloud_client.get_signed_url(file_record.object_url)
    return jsonify(download_url)


@downloadable_files_bp.route("/filter_facets", methods=["GET"])
@requires_auth("filter_facets")
def get_filter_facets():
    """
    Return a list of allowed filter facet values for a user.
    Response will have structure:
    {
        <facet 1>: [<value 1>, <value 2>,...],
        <facet 2>: [...],
        ...
    }
    """
    user = get_current_user()

    if user.role == CIDCRole.ADMIN.value:
        # Admins can facet on every trial or upload type
        trial_ids = DownloadableFiles.get_distinct("trial_id")
        upload_types = DownloadableFiles.get_distinct("upload_type")
    else:
        # Non-admins can only facet on what they have permission to view
        perms = Permissions.find_for_user(user.id)
        trial_ids = list({perm.trial_id for perm in perms})
        upload_types = list({perm.upload_type for perm in perms})

    return jsonify({"trial_id": trial_ids, "upload_type": upload_types})
