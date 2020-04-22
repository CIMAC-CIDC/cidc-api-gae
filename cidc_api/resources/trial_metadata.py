from flask import Blueprint
from werkzeug.exceptions import BadRequest

from ..shared.auth import requires_auth
from ..models import (
    CIDCRole,
    TrialMetadata,
    TrialMetadataSchema,
    TrialMetadataListSchema,
    UniqueViolation,
)
from ..shared.rest_utils import (
    lookup,
    marshal_response,
    unmarshal_request,
    use_args_with_pagination,
)

trial_metadata_bp = Blueprint("trials", __name__)

trial_metadata_schema = TrialMetadataSchema()
trial_metadata_list_schema = TrialMetadataListSchema()
partial_trial_metadata_schema = TrialMetadataSchema(partial=True)


@trial_metadata_bp.route("/", methods=["GET"])
@requires_auth("trial_metadata", [CIDCRole.ADMIN.value])
@use_args_with_pagination({}, trial_metadata_schema)
@marshal_response(trial_metadata_list_schema)
def list_trial_metadata(args, pagination_args):
    """List all trial metadata records."""
    trials = TrialMetadata.list(**pagination_args)
    count = TrialMetadata.count()

    return {"_items": trials, "_meta": {"total": count}}


@trial_metadata_bp.route("/", methods=["POST"])
@requires_auth("trial_metadata_item", [CIDCRole.ADMIN.value])
@unmarshal_request(trial_metadata_schema, "trial")
@marshal_response(trial_metadata_schema, 201)
def create_trial_metadata(trial):
    """Create a new trial metadata record."""
    try:
        trial.insert()
    except UniqueViolation as e:
        raise BadRequest(str(e))

    return trial


@trial_metadata_bp.route("/<int:trial>", methods=["GET"])
@requires_auth("trial_metadata_item", [CIDCRole.ADMIN.value])
@lookup(TrialMetadata, "trial")
@marshal_response(trial_metadata_schema)
def get_trial_metadata(trial):
    """Get one trial metadata record by ID."""
    return trial


@trial_metadata_bp.route("/<int:trial>", methods=["PATCH"])
@requires_auth("trial_metadata_item", [CIDCRole.ADMIN.value])
@lookup(TrialMetadata, "trial", check_etag=True)
@unmarshal_request(partial_trial_metadata_schema, "trial_updates")
@marshal_response(trial_metadata_schema, 200)
def update_trial_metadata(trial, trial_updates):
    """Update an existing trial metadata record."""
    trial.update(changes=trial_updates)

    return trial
