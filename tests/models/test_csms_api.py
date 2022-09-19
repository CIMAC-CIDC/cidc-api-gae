import os

os.environ["TZ"] = "UTC"
from copy import deepcopy
import pytest

from cidc_api.models import (
    TrialMetadata,
)
from cidc_api.models.csms_api import *
from cidc_api.config.settings import PRISM_ENCRYPT_KEY

from cidc_schemas.prism.core import (
    _check_encrypt_init,
    _encrypt,
    set_prism_encrypt_key,
)

from ..csms.data import manifests
from ..csms.utils import validate_json_blob

from ..resources.test_trial_metadata import setup_user


# make sure that the encryption key is set
try:
    _check_encrypt_init()
except:
    set_prism_encrypt_key(PRISM_ENCRYPT_KEY)


def manifest_change_setup(cidc_api, monkeypatch):
    setup_user(cidc_api, monkeypatch)

    # also checks for trial existence in JSON blobs
    metadata_json = {
        "protocol_identifier": "test_trial",
        "participants": [
            # existing participant with encrypted participant_id
            # to make sure that the CSMS API is encrypting new IDs as expected
            {
                "cimac_participant_id": "CTTTP04",
                "participant_id": _encrypt("LOCAL 04"),
                "cohort_name": "Arm_A",
                "samples": [],
            },
        ],
        "shipments": [],
        "allowed_cohort_names": ["Arm_A", "Arm_Z"],
        "allowed_collection_event_names": [
            "Baseline",
            "Pre_Day_1_Cycle_2",
            "On_Treatment",
        ],
    }
    TrialMetadata(trial_id="test_trial", metadata_json=metadata_json).insert()
    # need a second valid trial
    metadata_json["protocol_identifier"] = "foo"
    TrialMetadata(trial_id="foo", metadata_json=metadata_json).insert()

    for manifest in manifests:
        if manifest.get("status") not in (None, "qc_complete") or manifest.get(
            "excluded"
        ):
            continue

        # insert manifest before we check for changes
        insert_manifest_into_blob(deepcopy(manifest), uploader_email="test@email.com")
        # should check out, but let's make sure
        validate_json_blob(
            TrialMetadata.select_for_update_by_trial_id("test_trial").metadata_json
        )


def test_detect_changes_when_excluded(cidc_api, clean_db, monkeypatch):
    with cidc_api.app_context():
        manifest_change_setup(cidc_api, monkeypatch)
        manifest = [m for m in manifests if m.get("excluded")][0]

        assert detect_manifest_changes(manifest, uploader_email="test@email.com") == (
            []
        )


def test_change_protocol_identifier_error(cidc_api, clean_db, monkeypatch):
    with cidc_api.app_context():
        manifest_change_setup(cidc_api, monkeypatch)
        for manifest in manifests:
            if manifest.get("status") not in (None, "qc_complete") or manifest.get(
                "excluded"
            ):
                continue

            # Test critical changes throws Exception on samples
            # a bad ID raises a no trial found like insert_manifest_...
            with pytest.raises(Exception, match="No trial found with id"):
                # stored on samples, not manifest
                new_manifest = deepcopy(manifest)
                new_manifest["samples"] = [
                    {
                        k: v if k != "protocol_identifier" else "bar"
                        for k, v in sample.items()
                    }
                    for sample in new_manifest["samples"]
                ]
                detect_manifest_changes(new_manifest, uploader_email="test@email.com")

            # a good ID raises a new manifst error
            with pytest.raises(NewManifestError):
                # stored on samples, not manifest
                new_manifest = deepcopy(manifest)
                new_manifest["samples"] = [
                    {
                        k: v if k != "protocol_identifier" else "foo"
                        for k, v in sample.items()
                    }
                    for sample in new_manifest["samples"]
                ]
                detect_manifest_changes(new_manifest, uploader_email="test@email.com")


def test_change_manifest_id_error(cidc_api, clean_db, monkeypatch):
    with cidc_api.app_context():
        manifest_change_setup(cidc_api, monkeypatch)
        for n, manifest in enumerate(manifests):
            if manifest.get("status") not in (None, "qc_complete") or manifest.get(
                "excluded"
            ):
                continue

            # manifest_id has no such complication, but is also on the samples
            # changing the manifest_id makes it new
            with pytest.raises(NewManifestError):
                new_manifest = deepcopy(manifest)
                new_manifest["manifest_id"] = "foo"
                new_manifest["samples"] = [
                    {k: v if k != "manifest_id" else "foo" for k, v in sample.items()}
                    for sample in new_manifest["samples"]
                ]
                detect_manifest_changes(new_manifest, uploader_email="test@email.com")


def test_change_cimac_id_error(cidc_api, clean_db, monkeypatch):
    with cidc_api.app_context():
        manifest_change_setup(cidc_api, monkeypatch)
        for manifest in manifests:
            if manifest.get("status") not in (None, "qc_complete") or manifest.get(
                "excluded"
            ):
                continue

            # Changing a cimac_id is adding/removing a Sample
            ## so this is a different error
            with pytest.raises(Exception, match="Malformatted cimac_id"):
                new_manifest = deepcopy(manifest)
                new_manifest["samples"] = [
                    {k: v if k != "cimac_id" else "foo" for k, v in sample.items()}
                    if n == 0
                    else sample
                    for n, sample in enumerate(new_manifest["samples"])
                ]
                detect_manifest_changes(new_manifest, uploader_email="test@email.com")
            # need to use an actually valid cimac_id
            with pytest.raises(Exception, match="Missing sample"):
                new_manifest = deepcopy(manifest)
                new_manifest["samples"] = [
                    {
                        k: v if k != "cimac_id" else "CXXXP0555.00"
                        for k, v in sample.items()
                    }
                    if n == 0
                    else sample
                    for n, sample in enumerate(new_manifest["samples"])
                ]
                detect_manifest_changes(new_manifest, uploader_email="test@email.com")


def test_manifest_non_critical_changes(cidc_api, clean_db, monkeypatch):
    with cidc_api.app_context():
        manifest_change_setup(cidc_api, monkeypatch)
        # Test non-critical changes on the manifest itself
        keys = {k for manifest in manifests for k in manifest.keys()}
        for key in keys:
            if key in [
                # changing manifest_id would throw NewManifestError
                "manifest_id",
                # ignored by _calc_differences
                "barcode",
                "biobank_id",
                "entry_number",
                "excluded",
                "json_data",
                "modified_time",
                "modified_timestamp",
                "qc_comments",
                "sample_approved",
                "sample_manifest_type",
                "samples",
                "status",
                "submitter",
                # ignore ignored CSMS fields
                "submitter",
                "reason",
                "event",
                "study_encoding",
                "status_log",
            ]:
                continue

            # grab a completed manifest
            for manifest in manifests:
                if (
                    manifest.get("status") not in (None, "qc_complete")
                    or manifest.get("excluded")
                    or key not in manifest
                ):
                    continue

                new_manifest = deepcopy(manifest)
                new_manifest[key] = "foo"
                changes = detect_manifest_changes(
                    new_manifest, uploader_email="test@email.com"
                )

                assert len(changes) == 1 and changes[0] == Change(
                    entity_type="shipment",
                    manifest_id=manifest["manifest_id"],
                    trial_id=manifest["samples"][0]["protocol_identifier"],
                    changes={
                        key: (
                            manifest[key],
                            "foo",
                        )
                    },
                ), str(changes)


def test_manifest_non_critical_changes_on_samples(cidc_api, clean_db, monkeypatch):
    with cidc_api.app_context():
        manifest_change_setup(cidc_api, monkeypatch)
        # grab a completed manifest
        for manifest in manifests:
            if manifest.get("status") not in (None, "qc_complete") or manifest.get(
                "excluded"
            ):
                continue
            # Test non-critical changes for the manifest but stored on the samples
            for key in ["assay_priority", "assay_type", "sample_manifest_type"]:
                if key not in manifest["samples"][0]:
                    continue

                new_manifest = deepcopy(manifest)

                if key == "sample_manifest_type":
                    new_manifest["samples"] = [
                        {k: v for k, v in sample.items()}
                        for sample in new_manifest["samples"]
                    ]
                    for n in range(len(new_manifest["samples"])):
                        new_manifest["samples"][n].update(
                            {
                                "processed_sample_type": "foo",
                                "sample_manifest_type": "Tissue Scroll",
                                "processed_sample_derivative": "Germline DNA",
                            }
                        )
                else:
                    new_manifest["samples"] = [
                        {k: v if k != key else "foo" for k, v in sample.items()}
                        for sample in new_manifest["samples"]
                    ]

                changes = detect_manifest_changes(
                    new_manifest, uploader_email="test@email.com"
                )

                if key != "sample_manifest_type":
                    assert len(changes) == 1 and changes[0] == Change(
                        entity_type="shipment",
                        manifest_id=manifest["manifest_id"],
                        trial_id=manifest["samples"][0]["protocol_identifier"],
                        changes={key: (manifest["samples"][0][key], "foo")},
                    ), str(changes)


def test_sample_non_critical_changes(cidc_api, clean_db, monkeypatch):
    with cidc_api.app_context():
        manifest_change_setup(cidc_api, monkeypatch)
        # grab a completed manifest
        for manifest in manifests:
            if manifest.get("status") not in (None, "qc_complete") or manifest.get(
                "excluded"
            ):
                continue
            # Test non-critical changes on the samples
            for key in manifest["samples"][0].keys():
                if key in [
                    # ignore critical changes
                    "cimac_id",
                    "collection_event_name",
                    "manifest_id",
                    "protocol_identifier",
                    "recorded_collection_event_name",
                    "sample_key",
                    # ignore non-sample level changes
                    # see test_manifest_non_critical_changes_on_samples
                    "assay_priority",
                    "assay_type",
                    *manifest,
                    "processed_sample_derivative",
                    "processed_sample_type",
                    "receiving_party",
                    "trial_participant_id",
                    "type_of_sample",
                    # ignore list from calc_diff
                    "barcode",
                    "biobank_id",
                    "entry_number",
                    "event",
                    "excluded",
                    "json_data",
                    "modified_time",
                    "modified_timestamp",
                    "qc_comments",
                    "reason",
                    "sample_approved",
                    "sample_manifest_type",
                    "samples",
                    "status",
                    "status_log",
                    "study_encoding",
                    "submitter",
                ]:
                    continue

                new_manifest = deepcopy(manifest)

                if key in ["sample_derivative_concentration"]:
                    new_manifest["samples"] = [
                        {k: v if k != key else 10 for k, v in sample.items()}
                        if n == 0
                        else sample
                        for n, sample in enumerate(new_manifest["samples"])
                    ]
                else:
                    new_manifest["samples"] = [
                        {k: v if k != key else "foo" for k, v in sample.items()}
                        if n == 0
                        else sample
                        for n, sample in enumerate(new_manifest["samples"])
                    ]

                changes = detect_manifest_changes(
                    new_manifest, uploader_email="test@email.com"
                )

                # name change for when we're looking below
                if key == "standardized_collection_event_name":
                    key = "collection_event_name"
                elif key == "fixation_or_stabilization_type":
                    key = "fixation_stabilization_type"

                assert len(changes) == 1 and changes[0] == Change(
                    entity_type="sample",
                    manifest_id=manifest["manifest_id"],
                    cimac_id=manifest["samples"][0]["cimac_id"],
                    trial_id=manifest["samples"][0]["protocol_identifier"],
                    changes={
                        key: (
                            type(changes[0].changes[key][0])(
                                manifest["samples"][0][
                                    "standardized_collection_event_name"
                                    if key == "collection_event_name"
                                    and "standardized_collection_event_name"
                                    in manifest["samples"][0]
                                    else (
                                        "fixation_stabilization_type"
                                        if key == "fixation_stabilization_type"
                                        else key
                                    )
                                ]
                            ),
                            new_manifest["samples"][0][key],
                        )
                    },
                ), str(changes)


def test_insert_manifest_into_blob(cidc_api, clean_db, monkeypatch):
    """test that insertion of manifest into blob works as expected"""
    # grab a completed manifest
    manifest = [
        m
        for m in manifests
        if m.get("status") in (None, "qc_complete") and not m.get("excluded")
    ][0]

    with cidc_api.app_context():
        setup_user(cidc_api, monkeypatch)

        # blank db throws error
        with pytest.raises(Exception, match="No trial found with id"):
            insert_manifest_into_blob(manifest, uploader_email="test@email.com")

        metadata_json = {
            "protocol_identifier": "test_trial",
            "participants": [],
            "shipments": [],
            "allowed_cohort_names": [],
            "allowed_collection_event_names": [],
        }
        TrialMetadata(trial_id="test_trial", metadata_json=metadata_json).insert()

        with pytest.raises(Exception, match="not found within '/allowed_cohort_names/"):
            insert_manifest_into_blob(manifest, uploader_email="test@email.com")

        metadata_json["allowed_cohort_names"] = ["Arm_A", "Arm_Z"]
        TrialMetadata.select_for_update_by_trial_id("test_trial").update(
            changes={"metadata_json": metadata_json}
        )

        with pytest.raises(
            Exception, match="not found within '/allowed_collection_event_names/"
        ):
            insert_manifest_into_blob(manifest, uploader_email="test@email.com")

        metadata_json["allowed_collection_event_names"] = [
            "Baseline",
            "Pre_Day_1_Cycle_2",
        ]
        TrialMetadata.select_for_update_by_trial_id("test_trial").update(
            changes={"metadata_json": metadata_json}
        )

        target = deepcopy(manifest)
        with pytest.raises(NewManifestError):
            detect_manifest_changes(target, uploader_email="test@email.com")

        insert_manifest_into_blob(target, uploader_email="test@email.com")

        md_json = TrialMetadata.select_for_update_by_trial_id(
            "test_trial"
        ).metadata_json
        validate_json_blob(md_json)

        for other_manifest in [
            m
            for m in manifests
            if m.get("status") in [None, "qc_complete"] and not m.get("excluded")
            if m != manifest
        ]:
            insert_manifest_into_blob(other_manifest, uploader_email="test@email.com")

            md_json = TrialMetadata.select_for_update_by_trial_id(
                "test_trial"
            ).metadata_json
            validate_json_blob(md_json)

        with pytest.raises(Exception, match="already exists for trial"):
            insert_manifest_into_blob(manifest, uploader_email="test@email.com")
