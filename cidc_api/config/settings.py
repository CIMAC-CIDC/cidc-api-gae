"""
Settings and constants used by the CIDC API.

Any 'UPPER_CASE' variables will be exported as a key-value pair
in the `SETTINGS` dictionary defined at the bottom of this file.
"""

import shutil
from os import environ, path, mkdir

from dotenv import load_dotenv

from .db import get_sqlalchemy_database_uri
from .secrets import get_secrets_manager

load_dotenv()

### Configure application environment ###
ENV = environ.get("ENV")
assert ENV in (
    "dev",
    "staging",
    "prod",
), "ENV environment variable must be set to 'dev', 'staging', or 'prod'"
DEBUG = environ.get("DEBUG") == "True"
assert ENV == "dev" if DEBUG else True, "DEBUG mode is only allowed when ENV='dev'"
TESTING = environ.get("TESTING") == "True"
ALLOWED_CLIENT_URL = environ.get("ALLOWED_CLIENT_URL")
IS_GUNICORN = "gunicorn" in environ.get("SERVER_SOFTWARE", "")

### Configure miscellaneous constants ###
MIN_CLI_VERSION = "0.9.9"
PAGINATION_PAGE_SIZE = 25
MAX_PAGINATION_PAGE_SIZE = 200
INACTIVE_USER_DAYS = 60
MAX_THREADPOOL_WORKERS = 32
TEMPLATES_DIR = path.join("/tmp", "templates")
# Also, set up the directories for holding generated templates
if path.exists(TEMPLATES_DIR):
    shutil.rmtree(TEMPLATES_DIR)
mkdir(TEMPLATES_DIR)
for family in ["assays", "manifests", "analyses"]:
    family_dir = path.join(TEMPLATES_DIR, family)
    mkdir(family_dir)

### Configure prism encrypt ###
if not TESTING:
    secret_manager = get_secrets_manager()
    PRISM_ENCRYPT_KEY = secret_manager.get("PRISM_ENCRYPT_KEY")
else:
    PRISM_ENCRYPT_KEY = environ.get("PRISM_ENCRYPT_KEY")

### Configure Flask-SQLAlchemy ###
SQLALCHEMY_DATABASE_URI = get_sqlalchemy_database_uri(TESTING)
SQLALCHEMY_TRACK_MODIFICATIONS = False

### Configure Dev CFn ###
DEV_CFUNCTIONS_SERVER = environ.get("DEV_CFUNCTIONS_SERVER")

### Configure Auth0 ###
AUTH0_DOMAIN = environ.get("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = environ.get("AUTH0_CLIENT_ID")
ALGORITHMS = ["RS256"]

### Configure GCP ###
GOOGLE_CLOUD_PROJECT = environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_INTAKE_BUCKET = environ["GOOGLE_INTAKE_BUCKET"]
GOOGLE_UPLOAD_BUCKET = environ["GOOGLE_UPLOAD_BUCKET"]
GOOGLE_UPLOAD_TOPIC = environ["GOOGLE_UPLOAD_TOPIC"]
GOOGLE_ACL_DATA_BUCKET = environ["GOOGLE_ACL_DATA_BUCKET"]
GOOGLE_EPHEMERAL_BUCKET = environ["GOOGLE_EPHEMERAL_BUCKET"]
GOOGLE_UPLOAD_ROLE = environ["GOOGLE_UPLOAD_ROLE"]
GOOGLE_LISTER_ROLE = environ["GOOGLE_LISTER_ROLE"]
GOOGLE_INTAKE_ROLE = "roles/storage.objectAdmin"  # same across environments
GOOGLE_DOWNLOAD_ROLE = "roles/storage.objectViewer"  # same across environments
GOOGLE_BIGQUERY_USER_ROLE = "roles/bigquery.jobUser"  # same across environments
GOOGLE_PATIENT_SAMPLE_TOPIC = environ["GOOGLE_PATIENT_SAMPLE_TOPIC"]
GOOGLE_EMAILS_TOPIC = environ["GOOGLE_EMAILS_TOPIC"]
GOOGLE_ARTIFACT_UPLOAD_TOPIC = environ["GOOGLE_ARTIFACT_UPLOAD_TOPIC"]
GOOGLE_GRANT_DOWNLOAD_PERMISSIONS_TOPIC = environ[
    "GOOGLE_GRANT_DOWNLOAD_PERMISSIONS_TOPIC"
]
GOOGLE_AND_OPERATOR = " && "
GOOGLE_OR_OPERATOR = " || "

### File paths ###
this_directory = path.dirname(path.abspath(__file__))
MIGRATIONS_PATH = path.join(this_directory, "..", "..", "migrations")

# CSMS Integration Values
if not TESTING:
    secret_manager = get_secrets_manager()
    CSMS_BASE_URL = secret_manager.get("CSMS_BASE_URL")
    CSMS_TOKEN_URL = secret_manager.get("CSMS_TOKEN_URL")
    CSMS_CLIENT_SECRET = secret_manager.get("CSMS_CLIENT_SECRET")
    CSMS_CLIENT_ID = secret_manager.get("CSMS_CLIENT_ID")
else:
    CSMS_BASE_URL = environ.get("CSMS_BASE_URL")
    CSMS_TOKEN_URL = environ.get("CSMS_TOKEN_URL")
    CSMS_CLIENT_SECRET = environ.get("CSMS_CLIENT_SECRET")
    CSMS_CLIENT_ID = environ.get("CSMS_CLIENT_ID")


# Accumulate all constants defined in this file in a single dictionary
SETTINGS = {k: v for k, v in globals().items() if k.isupper()}
