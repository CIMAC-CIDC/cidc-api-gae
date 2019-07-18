from eve import Eve

from .info import info_api
from .ingestion import ingestion_api


def register_services(app: Eve):
    """Register service blueprints with the provided app"""
    app.register_blueprint(ingestion_api)
    app.register_blueprint(info_api)
