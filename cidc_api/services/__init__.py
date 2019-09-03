"""A collection of Eve event hooks and custom endpoints."""
from eve import Eve

from .files import register_files_hooks
from .info import info_api
from .ingestion import ingestion_api, register_ingestion_hooks
from .users import register_users_hooks


def register_services(app: Eve):
    """Register service blueprint with the provided app"""
    # Blueprint
    app.register_blueprint(ingestion_api)
    app.register_blueprint(info_api)

    # Hooks
    register_ingestion_hooks(app)
    register_users_hooks(app)
    register_files_hooks(app)
