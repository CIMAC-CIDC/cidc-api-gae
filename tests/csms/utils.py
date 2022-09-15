import os

os.environ["TZ"] = "UTC"
from sqlalchemy.orm.session import Session
from cidc_api.models.models import UploadJobs, with_default_session
from typing import Any, Dict
from datetime import date, datetime
from unittest.mock import MagicMock

from cidc_api.csms import auth
from cidc_api.models.csms_api import (
    cimac_id_to_cimac_participant_id,
)
from cidc_api.models.csms_api import _convert_csms_samples

from .data import manifests, samples


def _convert_to_date(date_str: str) -> date:
    if date_str.endswith("Z"):
        date_str = date_str.rstrip("Z")
    return datetime.strptime(date_str.replace("T", " "), "%Y-%m-%d %H:%M:%S")


def samples_history(cimac_id: str) -> Dict[str, Any]:
    """Return the history for a sample with a given CIMAC ID"""
    sample = [s for s in samples if s.get("cimac_id") == cimac_id]
    assert len(sample) == 1, "Given CIMAC id is not unique"
    sample = sample[0]

    ret = [
        {
            "data": sample,
            "diff": {k: [None, v] for k, v in sample.items()},
            "metadata": {
                "id": "0123456789ABCDEFGHIJKL",
                "version": 0,
                "txTime": "2021-01-01T00:00:00Z",
                "txId": "KJLIHGFEDCBA9876543210",
            },
        }
    ]
    if sample.get("status") in [None, "qc_complete"]:
        ret[0]["data"]["status"] = "cimac_id_generated"
        day = _convert_to_date(sample["modified_timestamp"]).day

        ret.append(
            {
                "data": sample,
                "diff": {"status": ["cimac_id_generated", sample.get("status")]},
                "metadata": {
                    "id": "123456789ABCDEFGHIJKL0",
                    "version": 1,
                    "txTime": f"2021-01-0{day}T00:00:00Z",
                    "txId": "0KJLIHGFEDCBA987654321",
                },
            }
        )

    return ret


def manifests_history(manifest_id: str) -> Dict[str, Any]:
    """Return the history for a manifest with a given ID"""
    manifest = [m for m in manifests if m.get("manifest_id") == manifest_id]
    assert len(manifest) == 1, "Given manifest ID is not unique"
    manifest = manifest[0]

    ret = [
        {
            "data": manifest,
            "diff": {k: [None, v] for k, v in manifest.items()},
            "metadata": {
                "id": "0123456789ABCDEFGHIJKL",
                "version": 0,
                "txTime": "2021-01-01T00:00:00Z",
                "txId": "KJLIHGFEDCBA9876543210",
            },
        }
    ]
    if manifest.get("status") in [None, "qc_complete"]:
        ret[0]["data"]["status"] = "draft"
        ret[0]["data"].pop("account_number", "")

        ret.append(
            {
                "data": manifest,
                "diff": {
                    "status": ["draft", manifest.get("status")],
                    "account_number": [None, manifest.get("account_number")],
                },
                "metadata": {
                    "id": "123456789ABCDEFGHIJKL0",
                    "version": 1,
                    "txTime": "2021-01-03T00:00:00Z",
                    "txId": "0KJLIHGFEDCBA987654321",
                },
            }
        )

    return ret


def validate_json_blob(trial_md: dict):
    """
    Given a trial metadata blob, validate that the data matches the test data provided by tests/csms/data.py
    Checks /shipments, /participants, and /participants/*/samples
    Also checks UploadJobs
    """
    global manifests, samples

    assert len(trial_md.get("shipments", [])) != 0
    for shipment in trial_md["shipments"]:
        manifest = [
            m
            for m in manifests
            if (
                m.get("manifest_id") == shipment["manifest_id"]
                and m.get("status") in (None, "qc_complete")
                and not m.get("excluded")
            )
        ]

        assert (
            len(manifest) == 1
        ), f"Given manifest ID is not unique, found {len(manifest)}"
        manifest = manifest[0]

        inst_samples = [
            s for s in samples if s.get("manifest_id") == manifest["manifest_id"]
        ]

        if any("assay_priority" in s for s in inst_samples):
            assert (
                len({s["assay_priority"] for s in inst_samples}) == 1
            ), f"assay_priority not uniquely defined for manifest {shipment['manifest_id']}"
            assert shipment["assay_priority"] == inst_samples[0]["assay_priority"]
        if any("assay_type" in s for s in inst_samples):
            assert (
                len({s["assay_type"] for s in inst_samples}) == 1
            ), f"assay_type not uniquely defined for manifest {shipment['manifest_id']}"
            assert shipment["assay_type"] == inst_samples[0]["assay_type"]

        for k, v in manifest.items():
            if k in shipment:
                assert shipment[k] == v, f"{shipment[k]} != {v}"

    for partic in trial_md["participants"]:
        inst_samples = [
            s
            for s in samples
            if cimac_id_to_cimac_participant_id(s.get("cimac_id"), None)
            == partic["cimac_participant_id"]
            and s.get("status") in [None, "qc_complete"]
        ]

        if any(["cohort_name" in s for s in inst_samples]):
            assert (
                len({s["cohort_name"] for s in inst_samples}) == 1
            ), f"cohort_name not uniquely defined for participant {partic['cimac_participant_id']}"
            assert partic["cohort_name"] == inst_samples[0]["cohort_name"]

        for sample in partic["samples"]:
            this_sample = [
                s for s in inst_samples if s.get("cimac_id") == sample["cimac_id"]
            ]
            assert (
                len(this_sample) == 1
            ), f"Sample not uniquely defined: {sample['cimac_id']}, found {len(this_sample)}"
            _, this_sample = next(
                _convert_csms_samples(
                    trial_md["protocol_identifier"], "manifest_id", this_sample, []
                )
            )

            assert (
                sample["collection_event_name"]
                == this_sample[
                    "standardized_collection_event_name"
                    if "standardized_collection_event_name" in sample
                    else "collection_event_name"
                ]
            )

            for k, v in this_sample.items():
                if k in sample:
                    assert (
                        sample[k] == v
                    ), f"on {sample['cimac_id']}: {sample[k]} != {v}"

    @with_default_session
    def check_upload_job(session: Session):
        for job in (
            session.query(UploadJobs)
            .filter(UploadJobs.trial_id == trial_md["protocol_identifier"])
            .all()
        ):
            validate_json_blob(job.metadata_patch)


def mock_get_with_authorization(monkeypatch):
    """Mock return for calls to CSMS"""

    def mock_get(url: str, **kwargs) -> MagicMock:
        ret = MagicMock()

        # return 500 if limit set too high
        if kwargs.get("limit", 5000) > 5000:
            ret.status_code = 500

        else:
            ret.status_code = 200

            # returning all entries in single page,
            # so return nothing if trying to get page 2
            if kwargs.get("offset", 0) > 0:
                ret.json.return_value = {"data": []}
            elif url == "/samples":
                ret.json.return_value = {"data": samples}
            elif url == "/manifests":
                ret.json.return_value = {"data": manifests}
            elif url == "/samples/history":
                cimac_id = url.split("/samples/history")[1].split("?")[0]
                ret.json.return_value = samples_history(cimac_id)
            elif url == "/manifests/history":
                manifest_id = url.split("/samples/history")[1].split("?")[0]
                ret.json.return_value = manifests_history(manifest_id)

        return ret

    monkeypatch.setattr(auth, "get_with_authorization", mock_get)
