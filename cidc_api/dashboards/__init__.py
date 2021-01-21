from flask import Flask

from .upload_jobs import upload_jobs_dashboard


def register_dashboards(app: Flask):
    """Add dashboard endpoints to the provided Flask app instance."""
    upload_jobs_dashboard.init_app(app)
