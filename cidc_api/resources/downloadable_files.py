from typing import List

from flask import Blueprint, jsonify
from webargs import fields
from webargs.flaskparser import use_args
from werkzeug.exceptions import NotFound
from marshmallow import validate


from ..models import (
    DownloadableFiles,
    DownloadableFileSchema,
    DownloadableFileListSchema,
    Permissions,
)
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
downloadable_files_list_schema = DownloadableFileListSchema()

file_filter_facets_schema = {
    "trial_ids": fields.List(fields.Str),
    "assay_types": fields.Dict(keys=fields.Str, values=fields.List(fields.Str)),
    "sample_types": fields.List(fields.Str),
    "clinical_types": fields.List(fields.Str),
}


@downloadable_files_bp.route("/", methods=["GET"])
@requires_auth("downloadable_files")
@use_args_with_pagination(file_filter_facets_schema, downloadable_files_schema)
@marshal_response(downloadable_files_list_schema)
def list_downloadable_files(args, pagination_args):
    """List downloadable files that the current user is allowed to view."""
    user = get_current_user()

    filter_ = DownloadableFiles.build_file_filter(args, user=user)

    files = DownloadableFiles.list(filter_=filter_, **pagination_args)
    count = DownloadableFiles.count(filter_=filter_)

    return {"_items": files, "_meta": {"total": count}}


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
    if not user.is_admin():
        perm = Permissions.find_for_user_trial_type(
            user.id, file_record.trial_id, file_record.upload_type
        )
        if not perm:
            raise NotFound(f"No file with id {file_id}.")

    # Generate the signed URL and return it.
    download_url = gcloud_client.get_signed_url(file_record.object_url)
    return jsonify(download_url)


@downloadable_files_bp.route("/filter_facets", methods=["GET"])
@requires_auth("filter_facets")
def get_filter_facets():
    """
    Return an object providing valid downloadable file filter facets.
    Response will have structure:
    {
        <facet 1>: [<value 1>, <value 2>,...] or {<top level>: [<second level 1>, <second level 2>]},
        <facet 2>: [...] or {...},
        ...
    }
    NOTE: the returned facets will not be restricted based on a user's permissions. That is,
    searching by some of the facets provided here may return empty if the user doesn't have
    permission to view files of the relevant type. It's up to the client to determine which 
    facets should be enabled for the requesting user.
    """
    user = get_current_user()

    trial_facets = DownloadableFiles.get_distinct("trial_id")
    assay_facets = DownloadableFiles.get_assay_facets()
    sample_facets = DownloadableFiles.get_sample_facets()
    clinical_facets = DownloadableFiles.get_clinical_facets()

    return {
        "trial_ids": trial_facets,
        "assay_types": assay_facets,
        "sample_types": sample_facets,
        "clinical_types": clinical_facets,
    }
