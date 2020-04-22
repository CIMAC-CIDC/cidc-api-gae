import json
from datetime import datetime

from flask import Blueprint, jsonify, abort, Request, current_app as app
from werkzeug.exceptions import Unauthorized, BadRequest

from ..shared import gcloud_client
from ..shared.auth import get_current_user, requires_auth
from ..shared.emails import new_user_registration, confirm_account_approval
from ..shared.rest_utils import (
    lookup,
    marshal_response,
    unmarshal_request,
    use_args_with_pagination,
)
from ..models import Users, UserSchema, UserListSchema, CIDCRole, IntegrityError

users_bp = Blueprint("users", __name__)

user_schema = UserSchema()
user_list_schema = UserListSchema()
new_user_schema = UserSchema(exclude=("approval_date", "role"))
partial_user_schema = UserSchema(partial=True)


@users_bp.route("/self", methods=["GET"])
@requires_auth("self")
@marshal_response(user_schema)
def get_self():
    """Return the current user's information to them."""
    return get_current_user()


@users_bp.route("/self", methods=["POST"])
@requires_auth("self")
@unmarshal_request(new_user_schema, "user")
@marshal_response(user_schema, 201)
def create_self(user):
    """
    Allow the current user to create a profile for themself. On success,
    send an email to the CIDC mailing list with a registration notification.
    """
    current_user = get_current_user()

    if current_user.email != user.email:
        raise BadRequest(
            f"{current_user.email} can't create a user with email {user.email}"
        )

    try:
        user.insert()
    except IntegrityError as e:
        raise BadRequest(str(e.orig))

    new_user_registration(user.email, send_email=True)

    return user


@users_bp.route("/", methods=["GET"])
@requires_auth("users", [CIDCRole.ADMIN.value])
@use_args_with_pagination({}, user_schema)
@marshal_response(user_list_schema)
def list_users(args, pagination_args):
    """
    List all users. TODO: pagination support
    """
    users = Users.list(**pagination_args)
    count = Users.count()
    return {"_items": users, "_meta": {"total": count}}


@users_bp.route("/<int:user>", methods=["GET"])
@requires_auth("users_item", [CIDCRole.ADMIN.value])
@lookup(Users, "user")
@marshal_response(user_schema)
def get_user(user: Users):
    """Get a single user by their id."""
    return user


@users_bp.route("/<int:user>", methods=["PATCH"])
@requires_auth("users_item", [CIDCRole.ADMIN.value])
@lookup(Users, "user", check_etag=True)
@unmarshal_request(partial_user_schema, "user_updates")
@marshal_response(user_schema)
def update_user(user: Users, user_updates: Users):
    """Update a single user's information."""
    # If a user is being awarded their first role, add an approval date
    if not user.role and user_updates.role:
        user_updates.approval_date = datetime.now()

    user.update(changes=user_updates)

    return user
