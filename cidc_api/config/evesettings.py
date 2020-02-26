import os
from cidc_api.config import db
from cidc_api.models import get_DOMAIN

TESTING = os.environ.get("TESTING")
TEMPLATES_DIR = os.path.join("/tmp", "templates")

## Configure database
SQLALCHEMY_DATABASE_URI = db.get_sqlachemy_database_uri(TESTING)
SQLALCHEMY_TRACK_MODIFICATIONS = False
## End database config

## Configure Eve REST API
RESOURCE_METHODS = ["GET", "POST"]
ITEM_METHODS = ["GET", "PATCH"]
CACHE_CONTROL = "no-cache"
DOMAIN = get_DOMAIN()
PAGINATION_DEFAULT = 200
PAGINATION_LIMIT = 200
MEDIA_ENDPOINT = None
## End Eve REST API config
