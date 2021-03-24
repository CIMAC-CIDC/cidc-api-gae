"""Configuration for the gunicorn WSGI server."""
import os
from gunicorn.arbiter import Arbiter

is_dev = os.environ.get("ENV") == "dev"

# See https://docs.gunicorn.org/en/stable/settings.html
port = os.environ.get("PORT", 8080)
loglevel = "DEBUG" if is_dev else "INFO"
reload = is_dev
timeout = 160
# Send all logs to stdout (where App Engine reads them from)
errorlog = "-"
