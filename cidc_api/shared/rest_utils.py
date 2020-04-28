"""Shared utility functions for building CIDC API resource endpoints."""
from functools import wraps
from typing import Optional, List, Callable

from flask import Flask, current_app as app, request, Response, jsonify
from webargs import fields
from webargs.flaskparser import use_args
from marshmallow import validate
from werkzeug.exceptions import (
    PreconditionRequired,
    PreconditionFailed,
    NotFound,
    BadRequest,
    InternalServerError,
    UnprocessableEntity,
)
from marshmallow.exceptions import ValidationError


from ..models import CommonColumns, BaseModel, BaseSchema
from ..config.settings import ENV


def delete_response():
    """Produce a Flask-friendly response for deletion requests."""
    return "deleted", 204


def unmarshal_request(schema: BaseSchema, kwarg_name: str, load_sqla: bool = True):
    """
    Generate a decorator that will load and validate the JSON body of 
    the current request object as an instance of `schema` and pass
    the loaded instance to the decorated function as a keyword argument
    with name `kwarg_name`. If `load_sqla` is False, then only validate the JSON
    body of the request, and pass it on to `kwarg_name` as a dictionary,
    not a SQLAlchemy model instance.
    """

    def decorator(endpoint):
        @wraps(endpoint)
        def wrapped(*args, **kwargs):
            if not request.json:
                raise BadRequest("expected JSON data in request body")

            if load_sqla:
                try:
                    body = schema.load(request.json)
                except ValidationError as e:
                    raise UnprocessableEntity(e.messages)
            else:
                body = request.json
                errors = schema.validate(body)
                if errors:
                    raise UnprocessableEntity(errors)

            kwargs[kwarg_name] = body

            return endpoint(*args, **kwargs)

        return wrapped

    return decorator


def marshal_response(schema: BaseSchema, status_code: int = 200):
    """
    Generate a decorator that will build a JSON representation of the 
    SQLAlchemy model instance returned by the wrapped function, and return 
    an HTTP response whose body contains that JSON representation.
    """

    def decorator(endpoint):
        @wraps(endpoint)
        def wrapped(*args, **kwargs):
            model_instance = endpoint(*args, **kwargs)

            # Dump the model to JSON
            json_result = schema.dump(model_instance)

            res = jsonify(json_result)
            res.status_code = status_code
            return res

        return wrapped

    return decorator


def lookup(
    model: CommonColumns,
    url_param: str,
    check_etag: bool = False,
    find_func: Optional[Callable[[str], BaseModel]] = None,
):
    """
    Given an route with a URL parameter (`url_param_name`) that will contain an id,
    search the `model` relation in the database for a record with that id. If `check_etag`
    is true, only proceed with the lookup if the client-provided etag matches the etag
    on the record if a record is found. Pass the record as a kwarg to the decorated function. 
    E.g.,

    @app.route('/<permission>', methods=['GET'])
    @lookup(Permissions, 'permission')
    def get_perm_record(permission):
        # Do something with the `permission` record here.
        # Without the @lookup decorator, `permission` would be a string
        # containing an identifier extracted from the URL, but with the decorator
        # it's a full SQLAlchemy model instance.
    """
    ETAG_HEADER = "if-match"

    if not find_func:
        find_func = model.find_by_id

    def decorator(endpoint):
        @wraps(endpoint)
        def wrapped(*args, **kwargs):
            if check_etag:
                etag = request.headers.get(ETAG_HEADER)
                if not etag:
                    raise PreconditionRequired(
                        "request must provide an If-Match header"
                    )

            record = find_func(kwargs[url_param])
            if not record:
                raise NotFound()

            if check_etag:
                if etag != record._etag:
                    raise PreconditionFailed(
                        "provided ETag does not match the stored ETag for this record"
                    )

            kwargs[url_param] = record

            return endpoint(*args, **kwargs)

        return wrapped

    return decorator


def use_args_with_pagination(argmap: dict, model_schema: BaseSchema):
    """
    Validate and parse query string arguments related to pagination and
    pass them as keyword arguments to the wrapped function:
        `page_num`, int: the page to start on
        `page_size`, int: the number of items per page
        `sort_field`, str: the table column to sort on
        `sort_direction`, 'asc' | 'desc': the direction of the sort
    """
    validate_sort_field = validate.OneOf(model_schema.fields.keys())
    validate_sort_dir = validate.OneOf(["asc", "desc"])

    pagination_argmap = {
        "page_num": fields.Int(),
        "page_size": fields.Int(),
        "sort_field": fields.Str(validate=validate_sort_field),
        "sort_direction": fields.Str(validate=validate_sort_dir),
    }

    # Ensure there are no collisions between argmaps
    for arg in argmap.keys():
        assert (
            arg not in pagination_argmap
        ), f"Provided arg `{arg}` collides with pagination args"

    full_argmap = {**pagination_argmap, **argmap}

    def get_user_args(args: dict):
        return {k: v for k, v in args.items() if k in argmap.keys()}

    def get_pagination_args(args: dict):
        return {k: v for k, v in args.items() if k in pagination_argmap.keys()}

    def decorator(endpoint):
        @wraps(endpoint)
        @use_args(full_argmap, location="query")
        def wrapped(args, *posargs, **kwargs):
            kwargs["args"] = get_user_args(args)
            kwargs["pagination_args"] = get_pagination_args(args)
            return endpoint(*posargs, **kwargs)

        return wrapped

    return decorator