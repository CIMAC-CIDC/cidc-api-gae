import traceback
from os.path import dirname, abspath, join

from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate, upgrade
from werkzeug.exceptions import HTTPException
from marshmallow.exceptions import ValidationError

from cidc_schemas.template import generate_all_templates

from .config.db import init_db
from .config.settings import SETTINGS
from .shared.auth import validate_api_auth
from .resources import register_resources

app = Flask(__name__, static_folder=None)
app.config.update(SETTINGS)

# Enable CORS
CORS(app, resources={r"*": {"origins": app.config["ALLOWED_CLIENT_URL"]}})

# Generate empty Excel templates
generate_all_templates(app.config["TEMPLATES_DIR"])

# Set up the database and run the migrations
init_db(app)

# Wire up the API
register_resources(app)

# Check that its auth configuration is validate
validate_api_auth(app)


@app.errorhandler(Exception)
def handle_errors(e: Exception):
    """Format exceptions as JSON, with status code and error message info."""
    if isinstance(e, HTTPException):
        data = {"code": e.code}
        if hasattr(e, "exc") and isinstance(e.exc, ValidationError):
            data["message"] = e.data["messages"]
        else:
            data["message"] = e.description
    else:
        # This is an internal server error, so log the traceback for debugging purposes.
        traceback.print_exception(type(e), e, e.__traceback__)
        data = {
            "code": 500,
            "message": "The server encountered an internal error and was unable to complete your request.",
        }

    response = jsonify(data)
    response.status_code = data["code"]
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
