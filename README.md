# CIDC API <!-- omit in TOC -->

| Environment | Branch                                                                   | Status                                                                                                                                |
| ----------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| production  | [production](https://github.com/CIMAC-CIDC/cidc_api-gae/tree/production) | [![Build Status](https://travis-ci.org/CIMAC-CIDC/cidc-api-gae.svg?branch=production)](https://travis-ci.org/CIMAC-CIDC/cidc_api-gae) |
| staging     | [master](https://github.com/CIMAC-CIDC/cidc_api-gae)                     | [![Build Status](https://travis-ci.org/CIMAC-CIDC/cidc-api-gae.svg?branch=master)](https://travis-ci.org/CIMAC-CIDC/cidc_api-gae)     |


The next generation of the CIDC API, reworked to use Google Cloud-managed services. This API is built with the Eve REST API framework backed by Google Cloud SQL, running on Google App Engine.

# Development <!-- omit in TOC -->****

- [Install Python dependencies](#install-python-dependencies)
- [Database Management](#database-management)
  - [Setting up a local development database](#setting-up-a-local-development-database)
  - [Connecting to a Cloud SQL database instance](#connecting-to-a-cloud-sql-database-instance)
  - [Running database migrations](#running-database-migrations)
- [Serving Locally](#serving-locally)
- [Testing](#testing)
- [Code Formatting](#code-formatting)
- [Deployment](#deployment)
  - [CI/CD](#cicd)
  - [Deploying by hand](#deploying-by-hand)
- [Connecting](#connecting)
- [Provisioning the system from scratch](#provisioning-the-system-from-scratch)

## Install Python dependencies
Install both the production and development dependencies.
```python
pip install -r requirements.txt -r requirements.dev.txt
```

## Database Management

### Setting up a local development database
In production, the CIDC API connects to a PostgreSQL instance hosted by Google Cloud SQL, but for local development, you should generally use a local PostgreSQL instance.

To do so, first install and start PostgreSQL:
```bash
brew install postgresql
brew services start postgresql # launches the postgres service whenever your computer launches
```
By default, the postgres service listens on port 5432. Next, create the `cidcdev` user, your local `cidc` development database, and a local `cidctest` database that the unit/integration tests will use:
```bash
psql -c "create user cidcdev with password '1234'"

# Database to use for local development
psql -c "create database cidc"
psql -c "grant all privileges on database cidc to cidcdev"

# Database to use for automated testing
psql -c "create database cidctest"
psql -c "grant all privileges on database cidctest to cidcdev"
```
Now, you should be able to connect to your development database with the URI `postgresql://cidcdev:1234@localhost:5432/cidc`. Or, in the postgres REPL:
```bash
psql cidc
```

Next, you'll need to set up the appropriate tables, indexes, etc. in your local database. To do so, `cd` into the `cidc_api` directory, then run:
```bash
FLASK_APP=app.py flask db upgrade
```
For more details on creating and running migrations, see [Running Migrations](#Running-Migrations).

### Connecting to a Cloud SQL database instance

Install the [Cloud SQL Proxy](https://cloud.google.com/sql/docs/mysql/quickstart-proxy-test):
```bash
curl -o /usr/local/bin/cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.darwin.amd64
chmod +x /usr/local/bin/cloud_sql_proxy
```

Proxy to the staging Cloud SQL instance:
```bash
cloud_sql_proxy --instance=cidc-dfci-staging:us-central1:cidc-postgres=tcp:5432
```

In your `.env` file, comment out `POSTGRES_URI` and uncomment all environment variables prefixed with `CLOUD_SQL_`. Restart your local API instance, and it will connect to the staging Cloud SQL instance via the local proxy.

If you wish to connect to the staging Cloud SQL instance via the postgres REPL, download and run the CIDC sql proxy tool (a wrapper for `cloud_sql_proxy`):
```bash
# Download the proxy
curl https://raw.githubusercontent.com/CIMAC-CIDC/cidc-devops/v2/scripts/cidc_sql_proxy.sh -o /usr/local/bin/cidc_sql_proxy
chmod +x /usr/local/bin/cidc_sql_proxy

# Run the proxy
cidc_sql_proxy staging # or cidc_sql_proxy prod
```

### Running database migrations
This project uses [`Flask Migrate`](https://flask-migrate.readthedocs.io/en/latest/) for managing database migrations. To create a new migration and upgrade the database specified in your `.env` config:
```bash
export FLASK_APP=cidc_api/app.py
# Generate the migration script
flask db migrate
# Apply changes to the database
flask db upgrade
```
To revert an applied migration, run:
```bash
flask db downgrade
```
If you're updating `models.py`, you should create a migration and commit the resulting 

## Serving Locally

Once you have a development database set up and running, run the API server:
```bash
python cidc_api/app.py
```

## Testing
This project uses [`pytest`](https://docs.pytest.org/en/latest/) for testing. 

To run the tests, simply run:
```bash
pytest
```

## Code Formatting
This project uses [`black`](https://black.readthedocs.io/en/stable/) for code styling. 

We recommend setting up autoformatting-on-save in your IDE of choice so that you don't have to worry about running `black` on your code.

## Deployment

### CI/CD

This project uses [Travis CI](https://travis-ci.org/) for continuous integration and deployment. To deploy an update to this application, follow these steps:
1. Create a new branch locally, commit updates to it, then push that branch to this repository.
2. Make a pull request from your branch into `master`. This will trigger Travis to run various tests and report back success or failure. You can't merge your PR until it passes the Travis build, so if the build fails, you'll probably need to fix your code.
3. Once the Travis build passes (and pending approval from collaborators reviewing the PR), merge your changes into `master`. This will trigger Travis to re-run tests on the code then deploy changes to the staging API.
4. Try out your deployed changes on the staging API once the Travis build completes.
5. If you're satisfied that staging should be deployed into production, make a PR from `master` into `production`. 
6. Once the PR build passes, merge `master` into `production`. This will trigger Travis to deploy the changes on staging to the production API.

For more information or to update the Travis pipeline, check out the configuration in `.travis.yml`.

### Deploying by hand
Should you ever need to deploy the application to Google App Engine by hand, you can do so by running the following:
```bash
gcloud app deploy <app.staging.yaml or app.prod.yaml> --project <gcloud project id>
```
That being said, avoid doing this! Deploying this way circumvents the safety checks built into the CI/CD pipeline and can lead to inconsistencies between the code running on GAE and the code present in this repository. Luckily, though, GAE's built-in versioning system makes it hard to do anything catastrophic :-)

## Connecting
Currently, the staging API is hosted at staging-api.cimac-network.org and the production instance is hosted at api.cimac-network.org.

To connect to the staging API with `curl` or a REST API client like Insomnia, get an id token from stagingportal.cimac-network.org, and include the header  `Authorization: Bearer YOUR_ID_TOKEN` in requests you make to the staging API. If your token expires, generate a new one following this same procedure.

To connect to the production API locally, follow the same procedure, but instead get your token from portal.cimac-network.org.

## Provisioning the system from scratch

For an overview of how to set up the CIDC API service from scratch, see the step-by-step guide in `PROVISION.md`.
