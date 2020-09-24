from flask import Blueprint
from webargs import fields
from werkzeug.exceptions import BadRequest

from ..shared.auth import requires_auth
from ..models import (
    CIDCRole,
    TrialMetadata,
    TrialMetadataSchema,
    TrialMetadataListSchema,
    IntegrityError,
)
from ..shared.rest_utils import (
    with_lookup,
    marshal_response,
    unmarshal_request,
    use_args_with_pagination,
)

trial_metadata_bp = Blueprint("trials", __name__)

trial_metadata_schema = TrialMetadataSchema()
trial_metadata_list_schema = TrialMetadataListSchema()
partial_trial_metadata_schema = TrialMetadataSchema(partial=True)

trial_modifier_roles = [CIDCRole.ADMIN.value, CIDCRole.NCI_BIOBANK_USER.value]


trial_filter_schema = {
    "include_file_bundles": fields.Bool(),
    "trial_ids": fields.DelimitedList(fields.Str),
}


@trial_metadata_bp.route("/", methods=["GET"])
@requires_auth("trial_metadata", trial_modifier_roles)
@use_args_with_pagination(trial_filter_schema, trial_metadata_schema)
@marshal_response(trial_metadata_list_schema)
def list_trial_metadata(args, pagination_args):
    """List all trial metadata records."""
    filter_ = TrialMetadata.build_trial_filter(**args)
    if "include_file_bundles" in args and args.pop("include_file_bundles"):
        trials = TrialMetadata.list_with_file_bundles(
            filter_=filter_, **pagination_args
        )
    else:
        trials = TrialMetadata.list(filter_=filter_, **pagination_args)
    count = TrialMetadata.count()

    return {"_items": trials, "_meta": {"total": count}}


@trial_metadata_bp.route("/", methods=["POST"])
@requires_auth("trial_metadata_item", trial_modifier_roles)
@unmarshal_request(trial_metadata_schema, "trial")
@marshal_response(trial_metadata_schema, 201)
def create_trial_metadata(trial):
    """Create a new trial metadata record."""
    try:
        trial.insert()
    except IntegrityError as e:
        raise BadRequest(str(e.orig))

    return trial


@trial_metadata_bp.route("/<string:trial>", methods=["GET"])
@requires_auth("trial_metadata_item", trial_modifier_roles)
@with_lookup(TrialMetadata, "trial", find_func=TrialMetadata.find_by_trial_id)
@marshal_response(trial_metadata_schema)
def get_trial_metadata_by_trial_id(trial):
    """Get one trial metadata record by trial identifier."""
    return trial


@trial_metadata_bp.route("/<string:trial>", methods=["PATCH"])
@requires_auth("trial_metadata_item", trial_modifier_roles)
@with_lookup(
    TrialMetadata, "trial", check_etag=True, find_func=TrialMetadata.find_by_trial_id
)
@unmarshal_request(partial_trial_metadata_schema, "trial_updates", load_sqla=False)
@marshal_response(trial_metadata_schema, 200)
def update_trial_metadata_by_trial_id(trial, trial_updates):
    """Update an existing trial metadata record by trial_id."""
    trial.update(changes=trial_updates)

    return trial
