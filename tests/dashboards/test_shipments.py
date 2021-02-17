from datetime import datetime

from dash.testing.composite import DashComposite

from cidc_api.models import (
    Users,
    UploadJobs,
    ROLES,
    UploadJobStatus,
    CIDCRole,
    TrialMetadata,
)
from cidc_api.dashboards.shipments import shipments_dashboard, TRIAL_DROPDOWN

from ..utils import make_role, mock_current_user


def test_shipments_dashboard(cidc_api, clean_db, monkeypatch, dash_duo: DashComposite):
    """
    Check that only CIDC Admins can view data in the upload jobs table dashboard.
    NOTE: this is a non-exhaustive smoketest. It does not test the functionality of
    the shipments dashboard.
    """
    trial_id = "test-trial"
    user = Users(email="test@email.com", approval_date=datetime.now())
    trial = TrialMetadata(
        trial_id=trial_id,
        metadata_json={
            "protocol_identifier": "test-trial",
            "participants": [],
            "allowed_cohort_names": [],
            "allowed_collection_event_names": [],
        },
    )
    upload_job = UploadJobs(
        uploader_email=user.email,
        trial_id=trial.trial_id,
        upload_type="pbmc",
        gcs_xlsx_uri="",
        metadata_patch={},
        multifile=False,
    )
    upload_job._set_status_no_validation(UploadJobStatus.MERGE_COMPLETED.value)

    with cidc_api.app_context():
        user.insert()
        trial.insert()
        upload_job.insert()

        clean_db.refresh(user)
        clean_db.refresh(upload_job)

    for role in ROLES:
        make_role(user.id, role, cidc_api)
        mock_current_user(user, monkeypatch)

        dash_duo.server(shipments_dashboard)
        dash_duo.wait_for_page(f"{dash_duo.server.url}/dashboards/upload_jobs/")

        if CIDCRole(role) == CIDCRole.ADMIN:
            dash_duo.click_at_coord_fractions(f"#{TRIAL_DROPDOWN}", 0.1, 0.1)
            dash_duo.wait_for_contains_text(f"#{TRIAL_DROPDOWN}", trial_id)
        else:
            dash_duo._wait_for_callbacks()
            assert any(
                ["401 (UNAUTHORIZED)" in log["message"] for log in dash_duo.get_logs()]
            )
