from os.path import dirname, abspath, join

from eve import Eve
from eve.auth import TokenAuth
from eve_sqlalchemy import SQL
from eve_sqlalchemy.validation import ValidatorSQL
from eve_swagger import swagger
from flask import jsonify
from flask_migrate import Migrate, upgrade
from flask_cors import CORS

from models import BaseModel
from auth import BearerAuth
from services import register_services

ABSPATH = dirname(abspath(__file__))
SETTINGS = join(ABSPATH, "config", "settings.py")
MIGRATIONS = join(ABSPATH, "..", "migrations")

# Instantiate the Eve app
app = Eve(auth=BearerAuth, data=SQL, validator=ValidatorSQL, settings=SETTINGS)

# Enable CORS
# TODO: be more selective about which domains can make requests
CORS(app)

# Register custom services
register_services(app)

# Bind the data model to the app's database engine
db = app.data.driver
BaseModel.metadata.bind = db.engine
db.Model = BaseModel

# Configure flask-migrate and upgrade the database
# Note: while upgrades are performed automatically,
# generating the migrations should be performed by hand
# using the flask-migrate CLI, and the resulting files
# should be checked into source control.
Migrate(app, db, MIGRATIONS)
with app.app_context():
    app.logger.info("Upgrading the database...")
    upgrade(MIGRATIONS)
    app.logger.info("Done upgrading the database.")

# Configure the swagger site
# TODO: flesh this out
app.register_blueprint(swagger)
app.config["SWAGGER_INFO"] = {
    "title": "CIDC API",
    "version": "0.1",
    "termsOfService": "[TODO]",
    "contact": {
        "name": "support",
        "url": "https://github.com/cimac-cidc/cidc_api-gae/blob/master/README.md",
    },
    "license": {
        "name": "MIT",
        "url": "https://github.com/dfci/cidc_api-gae/blob/master/LICENSE",
    },
    "schemes": ["http", "https"],
}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
