from os import environ

from eve_sqlalchemy.config import DomainConfig, ResourceConfig
from dotenv import load_dotenv

from models import Users, TrialMetadata

load_dotenv()

TESTING = environ.get("TESTING") == "True"

# Configure secrets manager
if TESTING:
    from unittest.mock import MagicMock

    # If we're testing, we shouldn't need access to secrets in GCS
    secrets = MagicMock()
else:
    from secrets import CloudStorageSecretManager

    secrets_bucket = environ.get("SECRETS_BUCKET_NAME")
    secrets = CloudStorageSecretManager(secrets_bucket)

# Auth0 configuration
AUTH0_DOMAIN = environ.get("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = environ.get("AUTH0_CLIENT_ID")
ALGORITHMS = ["RS256"]

# Deployment environment
ENV = environ.get("ENV", "staging")
assert ENV in ("dev", "staging", "prod")

DEBUG = ENV == "dev" and environ.get("DEBUG")

# Database configuration
POSTGRES_URI = environ.get("POSTGRES_URI")
if not POSTGRES_URI:
    from sqlalchemy.engine.url import URL

    # If POSTGRES_URI env variable is not set,
    # we're connecting to a Cloud SQL instance.

    config: dict = {
        "drivername": "postgres",
        "username": environ.get("CLOUD_SQL_DB_USER"),
        "password": secrets.get("CLOUD_SQL_DB_PASS"),
        "database": environ.get("CLOUD_SQL_DB_NAME"),
    }

    if environ.get("CLOUD_SQL_INSTANCE_NAME"):
        # If CLOUD_SQL_INSTANCE_NAME is defined, we're connecting
        # via a unix socket from inside App Engine.
        config["query"] = {
            "host": "/cloudsql/%s" % environ.get("CLOUD_SQL_INSTANCE_NAME")
        }
    elif environ.get("CLOUD_SQL_PROXY_HOST") and environ.get("CLOUD_SQL_PROXY_PORT"):
        # If CLOUD_SQL_PROXY_HOST/PORT are defined, we're connecting
        # to Cloud SQL via a local cloud_sql_proxy.
        config["host"] = environ.get("CLOUD_SQL_PROXY_HOST")
        config["port"] = environ.get("CLOUD_SQL_PROXY_PORT")
    else:
        raise Exception(
            "Either POSTGRES_URI, CLOUD_SQL_INSTANCE_NAME, or "
            + "CLOUD_SQL_PROXY_HOST/PORT must be defined to connect "
            + "to a database."
        )

    POSTGRES_URI = str(URL(**config))

SQLALCHEMY_DATABASE_URI = POSTGRES_URI
SQLALCHEMY_TRACK_MODIFICATIONS = False


RESOURCE_METHODS = ["GET", "POST"]
ITEM_METHODS = ["GET", "PUT", "PATCH"]

_domain_config = {
    "users": ResourceConfig(Users),
    "trial-metadata": ResourceConfig(TrialMetadata),
}
DOMAIN = DomainConfig(_domain_config).render()
