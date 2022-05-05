import traceback

from flask import Flask, jsonify
from flask_cors import CORS
from flask_talisman import Talisman
from werkzeug.exceptions import HTTPException
from marshmallow.exceptions import ValidationError

from .config.db import init_db
from .config.settings import SETTINGS
from .config.logging import get_logger
from .shared.auth import validate_api_auth
from .resources import register_resources
from .dashboards import register_dashboards

logger = get_logger(__name__)

app = Flask(__name__, static_folder=None)
app.config.update(SETTINGS)

# Enable CORS and HSTS
CORS(app, resources={r"*": {"origins": app.config["ALLOWED_CLIENT_URL"]}})
csp = {
    "default-src": [
        "'self'",
        "stackpath.bootstrapcdn.com",
        "code.jquery.com",
        "cdn.jsdelivr.net",
    ]
}
Talisman(
    app,
    # disable https if app is run in testing mode
    # flask's test_client doesn't use https for some reason
    force_https=not app.config["TESTING"],
    content_security_policy=csp,
)

# Set up the database and run the migrations
init_db(app)

# Wire up the API
register_resources(app)

# Check that its auth configuration is validate
validate_api_auth(app)

# Add dashboard endpoints to the API
register_dashboards(app)


@app.errorhandler(Exception)
def handle_errors(e: Exception):
    """Format exceptions as JSON, with status code and error message info."""
    if isinstance(e, HTTPException):
        status_code = e.code
        _error = {}
        if hasattr(e, "exc") and isinstance(e.exc, ValidationError):
            _error["message"] = e.data["messages"]
        else:
            _error["message"] = e.description

        # general HTTP error log
        logger.error(f"HTTP {status_code}: {_error['message']}")
    else:
        status_code = 500
        # This is an internal server error, so log the traceback for debugging purposes.
        traceback.print_exception(type(e), e, e.__traceback__)
        _error = {
            "message": "The server encountered an internal error and was unable to complete your request."
        }

    # Format errors to be backwards-compatible with Eve-style errors
    eve_style_error_json = {"_status": "ERR", "_error": _error}
    response = jsonify(eve_style_error_json)
    response.status_code = status_code

    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=False)
