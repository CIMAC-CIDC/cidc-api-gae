import pytest
from dash.testing.errors import DashAppLoadingError
from dash.testing.composite import DashComposite

from cidc_api.dashboards import upload_jobs_table


def test_upload_jobs_table(dash_duo: DashComposite):
    with pytest.raises(DashAppLoadingError):
        dash_duo.start_server(upload_jobs_table)
