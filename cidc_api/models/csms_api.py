__all__ = [
    "Change",
    "detect_manifest_changes",
    "insert_manifest_into_blob",
    "NewManifestError",
]

import os
import re

os.environ["TZ"] = "UTC"
from collections import defaultdict
from datetime import date, datetime, time
from sqlalchemy.orm.session import Session
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from cidc_schemas.prism.core import (
    _check_encrypt_init,
    _encrypt,
    _ENCRYPTED_FIELD_LEN,
    load_and_validate_schema,
    set_prism_encrypt_key,
)
from .models import TrialMetadata, UploadJobStatus, UploadJobs
from .models import with_default_session
from ..config.logging import get_logger
from ..config.settings import PRISM_ENCRYPT_KEY

logger = get_logger(__name__)

cimac_id_to_cimac_participant_id = lambda cimac_id, _: cimac_id[:7]
cimac_id_regex_pattern = "^C[A-Z0-9]{3}[A-Z0-9]{3}[A-Z0-9]{2}.[0-9]{2}$"
cimac_id_regex = re.compile(cimac_id_regex_pattern)


SAMPLE_SCHEMA: dict = load_and_validate_schema("sample.json")
PARTICIPANT_SCHEMA: dict = load_and_validate_schema("participant.json")
SHIPMENT_SCHEMA: dict = load_and_validate_schema("shipping_core.json")
TARGET_PROPERTIES_MAP: Dict[str, dict] = {
    "sample": SAMPLE_SCHEMA["properties"],
    "participant": PARTICIPANT_SCHEMA["properties"],
    "shipment": SHIPMENT_SCHEMA["properties"],
}

# make sure that the encryption key is set
try:
    _check_encrypt_init()
except:
    set_prism_encrypt_key(PRISM_ENCRYPT_KEY)


def _get_all_values(target: str, old: dict, drop: List[str] = []) -> Dict[str, Any]:
    """
    Parameters
    ----------
    target: str in ["sample", "participant", "shipment"]
    old: dict
    drop: List[str] = []

    Returns
    -------
    Dict[str, Any]
        all of the values from `old` that are in `target` excepting anything keys in `drop`
    """

    ret = {
        p: old[p]
        for p in TARGET_PROPERTIES_MAP[target].keys()
        if p in old and p not in drop
    }

    return ret


class NewManifestError(Exception):
    pass


def _parse_upload_type(sample: dict, upload_type: Set[str]) -> str:
    sample_manifest_type = sample.get("sample_manifest_type")
    processed_derivative = sample.get("processed_sample_derivative")
    if sample_manifest_type is None:
        # safety
        return

    elif sample_manifest_type == "biofluid_cellular":
        upload_type.add("pbmc")
    elif sample_manifest_type == "tissue_slides":
        upload_type.add("tissue_slide")

    elif processed_derivative == "Germline DNA":
        upload_type.add(f"normal_{sample_manifest_type.split()[0].lower()}_dna")
    elif processed_derivative == "Tumor DNA":
        upload_type.add(f"tumor_{sample_manifest_type.split()[0]}_dna")
    elif processed_derivative in ["DNA", "RNA"]:
        unprocessed_type = sample.get("type_of_sample")
        new_type = "tumor" if "tumor" in unprocessed_type.lower() else "normal"
        new_type += (
            "_blood_" if sample_manifest_type.startswith("biofluid") else "_tissue_"
        )
        new_type += processed_derivative.lower()

        upload_type.add(new_type)


def _get_upload_type(samples: Iterable[Dict[str, Any]]) -> str:
    upload_type: Set[str] = set()

    for sample in samples:
        processed_type = sample.get("processed_sample_type").lower()
        if processed_type == "h&e-stained fixed tissue slide specimen":
            processed_type = "h_and_e"

        if processed_type in [
            "pbmc",
            "plasma",
            "tissue_slide",
            "normal_blood_dna",
            "normal_tissue_dna",
            "tumor_tissue_dna",
            "tumor_tissue_rna",
            "h_and_e",
        ]:
            upload_type.add(processed_type)
        else:
            # updates upload_type in-place with the given sample
            _parse_upload_type(sample=sample, upload_type=upload_type)

    assert (
        len(upload_type) == 1
    ), f"Inconsistent value determined for upload_type:{upload_type}"
    return list(upload_type)[0]


def _get_and_check(
    obj: Union[Dict[str, Any], List[Dict[str, Any]]],
    key: str,
    msg: str,
    default: Any = None,
    check: Callable[[Any], bool] = bool,
) -> Any:
    """
    Returns a key from a dictionary if it exists, and raises an error if fails an integrity check
    If given a list of dictionaries, asserts that each one provides the same result.
    """
    if isinstance(obj, list):
        ret = {o.get(key, default) for o in obj}
        assert len(ret) == 1, f"Inconsistent value provided for {key}"
        ret = list(ret)[0]
    else:
        ret = obj.get(key, default)

    if not check(ret):
        raise Exception(msg)
    else:
        return ret


def _extract_info_from_manifest(
    manifest: Dict[str, Any]
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Given a manifest, do initial validation and return some key values

    Returns
    -------
    str : trial_id
        the same across all samples
        exists in both TrialMetadata and ClinicalTrial tables
    str : manifest_id
    List[Dict[str, Any]] : samples

    Exceptions Raised
    -----------------
    - "Cannot add a manifest that is not qc_complete"
        if manifest's status is not qc_complete (or null)
    - f"Manifest {manifest_id} contains no samples: {manifest}"
    - f"No consistent protocol_identifier defined for samples on manifest {manifest_id}"
    """
    manifest_id = _get_and_check(
        obj=manifest, key="manifest_id", msg=f"No manifest_id in: {manifest}"
    )
    _ = _get_and_check(  # don't need to keep status
        obj=manifest,
        key="status",
        msg="Cannot add a manifest that is not qc_complete",
        default="qc_complete",
        check=lambda v: v == "qc_complete",
    )
    samples = _get_and_check(
        obj=manifest,
        key="samples",
        msg=f"Manifest {manifest_id} contains no samples: {manifest}",
        default=[],
        check=lambda v: len(v) != 0,
    )
    trial_id = _get_and_check(
        obj=samples,
        key="protocol_identifier",
        msg=f"No consistent protocol_identifier defined for samples on manifest {manifest_id}",
    )

    return trial_id, manifest_id, samples


def _extract_details_from_trial(csms_samples: List[Dict[str, Any]]):
    """
    Given a trial, return some key values

    Returns
    -------
    str : assay_priority
    str : assay_type

    Exceptions Raised
    -----------------
    - f"No assay_priority defined for manifest_id={manifest_id} for trial {trial_id}"
    - f"No assay_type defined for manifest_id={manifest_id} for trial {trial_id}"
    """
    assay_priority = _get_and_check(
        obj=csms_samples,
        key="assay_priority",
        msg="will not be thrown",
        check=lambda _: True,
    )
    assay_type = _get_and_check(
        obj=csms_samples,
        key="assay_type",
        msg="will not be thrown",
        check=lambda _: True,
    )
    return assay_priority, assay_type


def _process_csms_sample(csms_sample: dict):
    event_name = csms_sample.get("standardized_collection_event_name")
    if event_name is None:
        raise Exception(
            f"No standardized_collection_event_name defined for sample {csms_sample.get('cimac_id', '')} on manifest {csms_sample['manifest_id']} for trial {csms_sample['protocol_identifier']}"
        )
    else:
        csms_sample["collection_event_name"] = event_name

    # encrypt participant ids if not already encrypted
    if (
        "participant_id" in csms_sample
        and len(csms_sample["participant_id"]) != _ENCRYPTED_FIELD_LEN
    ):
        csms_sample["participant_id"] = _encrypt(csms_sample["participant_id"])

    # differences in naming convention
    processed_sample_type_map: Dict[str, str] = {
        "tissue_slide": "Fixed Slide",
        "tumor_tissue_dna": "Tissue Scroll",
        "plasma": "Plasma",
        "normal_tissue_dna": "Tissue Scroll",
        "h_and_e": "H&E-Stained Fixed Tissue Slide Specimen",
        "pbmc": "PBMC",
    }
    if csms_sample["processed_sample_type"] in processed_sample_type_map:
        csms_sample["processed_sample_type"] = processed_sample_type_map[
            csms_sample["processed_sample_type"]
        ]

    # differences in keys
    if "fixation_or_stabilization_type" in csms_sample:
        csms_sample["fixation_stabilization_type"] = csms_sample.pop(
            "fixation_or_stabilization_type"
        )

    # typing
    if "sample_derivative_concentration" in csms_sample:
        csms_sample["sample_derivative_concentration"] = float(
            csms_sample["sample_derivative_concentration"]
        )

    # "Not Reported" as default when required
    if (
        csms_sample["type_of_sample"] == "Blood"
        and "type_of_primary_container" not in csms_sample
    ):
        csms_sample["type_of_primary_container"] = "Not Reported"
    if "parent_sample_id" not in csms_sample:
        csms_sample["parent_sample_id"] = "Not Reported"


def _convert_csms_samples(
    trial_id: str,
    manifest_id: str,
    csms_samples: List[Dict[str, Any]],
    existing_cimac_ids: List[str] = [],
) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """
    Convert a list of CSMS-style samples into an iterator returning CIMAC IDs and CIDC-style samples
    Exceptions are raised during the call for each sample; full validation is NOT done first.

    Returns
    -------
    iterator yielding (str, dict)
        cimac_id, converted CSMS sample

    Exceptions Raised
    -----------------
    - f"No standardized_collection_event_name defined for sample {sample['cimac_id']} on manifest {sample['manifest_id']} for trial {sample['protocol_identifier']}"
    - f"No cimac_id defined for samples[{n}] on manifest_id={manifest_id} for trial {trial_id}"
    - f"Malformatted cimac_id={cimac_id} on manifest_id={manifest_id} for trial {trial_id}"
    - f"Sample with cimac_id={cimac_id} already exists for trial {trial_id}\nNew samples: {sample}"
    - f"Sample with no local participant_id given:\n{sample}"
        if participant_id and trial_participant_id are both undefined
    """
    for n, sample in enumerate(csms_samples):
        # process the sample
        _process_csms_sample(csms_sample=sample)

        # get and validate the CIMAC id
        cimac_id = _get_and_check(
            obj=sample,
            key="cimac_id",
            msg=f"No cimac_id defined for samples[{n}] on manifest_id={manifest_id} for trial {trial_id}",
        )
        if not cimac_id_regex.match(cimac_id):
            raise Exception(
                f"Malformatted cimac_id={cimac_id} on manifest_id={manifest_id} for trial {trial_id}"
            )
        elif cimac_id in existing_cimac_ids:
            raise Exception(
                f"Sample with cimac_id={cimac_id} already exists for trial {trial_id}\nNew samples: {sample}"
            )

        # yield
        yield (cimac_id, sample)


@with_default_session
def insert_manifest_into_blob(
    manifest: Dict[str, Any],
    uploader_email: str,
    *,
    dry_run: bool = False,
    session: Session,
) -> None:
    """
    Given a CSMS-style manifest, add it into the JSON metadata blob
    If `dry_run`, calls `session.rollback` instead of `session.commit`

    Exceptions Raised
    -----------------
    - "Cannot add a manifest that is not qc_complete"
        if manifest's status is not qc_complete (or null)
    - f"Manifest {manifest_id} contains no samples: {manifest}"
    - f"No consistent protocol_identifier defined for samples on manifest {manifest_id}"
    - f"Clinical trial with protocol identifier={trial_id} does not exist"
        if trial is missing from TrialMetadata OR ClinicalTrial OR both

    - Assertion: "Inconsistent value provided for assay_priority"
    - Assertion: "Inconsistent value provided for assay_type"

    - f"Manifest with manifest_id={manifest_id} already exists for trial {trial_id}"
    - f"No standardized_collection_event_name defined for sample {sample['cimac_id']} on manifest {sample['manifest_id']} for trial {sample['protocol_identifier']}"
    - f"No cimac_id defined for samples[{n}] on manifest_id={manifest_id} for trial {trial_id}"
    - f"Malformatted cimac_id={cimac_id} on manifest_id={manifest_id} for trial {trial_id}"
    - f"Sample with cimac_id={cimac_id} already exists for trial {trial_id}\nNew samples: {sample}"
    - f"Sample with no local participant_id given:\n{sample}"
        if participant_id and trial_participant_id are both undefined

    - "prism errors: [{errors from merge_clinical_trial_metadata}]"
    """
    # schemas import here to keep JSON-blob code together
    from cidc_schemas.prism.merger import merge_clinical_trial_metadata

    trial_id, manifest_id, csms_samples = _extract_info_from_manifest(manifest)
    trial_md = TrialMetadata.select_for_update_by_trial_id(trial_id, session=session)
    if manifest_id in [s["manifest_id"] for s in trial_md.metadata_json["shipments"]]:
        raise Exception(
            f"Manifest with manifest_id={manifest_id} already exists for trial {trial_id}"
        )

    # pull out some additional values we'll need
    existing_cimac_ids = [
        s["cimac_id"]
        for p in trial_md.metadata_json["participants"]
        for s in p["samples"]
    ]
    assay_priority, assay_type = _extract_details_from_trial(csms_samples)
    if assay_priority:
        manifest["assay_priority"] = assay_priority
    if assay_type:
        manifest["assay_type"] = assay_type

    # a patch is just the parts that are new, equivalent to the return of schemas.prismify
    patch = {
        "protocol_identifier": trial_id,
        "shipments": [
            _get_all_values(
                target="shipment", old=manifest, drop=["excluded", "json_data"]
            )
        ],
        "participants": [],
    }

    # sort samples by participants
    sample_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for cimac_id, sample in _convert_csms_samples(
        trial_id, manifest_id, csms_samples, existing_cimac_ids
    ):
        sample_map[cimac_id_to_cimac_participant_id(cimac_id, {})].append(sample)

    # each participant has a list of samples
    for cimac_participant_id, partic_samples in sample_map.items():
        partic = dict(
            cimac_participant_id=cimac_participant_id,
            participant_id=partic_samples[0]["participant_id"],
            **_get_all_values(
                target="participant",
                old=partic_samples[0],
                drop=[
                    "cimac_participant_id",
                    "excluded",
                    "json_data",
                    "participant_id",
                    "trial_participant_id",
                ],
            ),
        )
        partic["samples"] = [
            _get_all_values(
                target="sample",
                old=sample,
                drop=["excluded", "json_data", "manifest_id"],
            )
            for sample in partic_samples
        ]

        patch["participants"].append(partic)

    logger.info(f"Patch for {trial_id} manifest {manifest_id}:\n{patch}")
    # merge and validate the data
    # the existence of the correct cohort and collection_event names are checked here
    merged, errs = merge_clinical_trial_metadata(patch, trial_md.metadata_json)
    if len(errs):
        raise Exception({"prism errors": [str(e) for e in errs]})

    # save it
    trial_md.update(changes={"metadata_json": merged}, commit=False, session=session)

    # create pseudo-UploadJobs
    UploadJobs(
        trial_id=trial_id,
        _status=UploadJobStatus.MERGE_COMPLETED.value,
        multifile=False,
        metadata_patch=patch,
        upload_type=_get_upload_type(csms_samples),
        uploader_email=uploader_email,
    ).insert(commit=False, session=session)

    if dry_run:
        session.flush()
        session.rollback()
    else:
        session.commit()


class Change:
    def __init__(
        self,
        entity_type: str,
        trial_id: str,
        manifest_id: str,
        cimac_id: str = None,
        changes: Dict[str, Tuple[Any, Any]] = [],
    ):
        if entity_type not in ["sample", "shipment", "upload"]:
            raise ValueError(
                f"entity_type must be in: sample, shipment, upload\nnot: {entity_type}"
            )
        else:
            self.entity_type = entity_type

        self.trial_id = trial_id
        self.manifest_id = manifest_id
        self.cimac_id = cimac_id
        self.changes = changes

    def __bool__(self):
        return bool(len(self.changes))

    def __repr__(self):
        return f"{self.entity_type.title()} changes for {self.trial_id}, {self.manifest_id}, {self.cimac_id}:\n{self.changes}"

    def __eq__(self, other):
        return (
            self.entity_type == other.entity_type
            and self.trial_id == other.trial_id
            and self.manifest_id == other.manifest_id
            and self.cimac_id == other.cimac_id
            and self.changes == other.changes
        )


def _calc_difference(
    entity_type: str,
    trial_id: str,
    manifest_id: str,
    cidc: Dict[str, Any],
    csms: Dict[str, Any],
    ignore=[
        "barcode",
        "biobank_id",
        "cimac_participant_id",
        "entry_number",
        "event",
        "excluded",
        "json_data",
        "modified_time",
        "modified_timestamp",
        "protocol_identifier",
        "qc_comments",
        "reason",
        "sample_approved",
        "sample_manifest_type",
        "samples",
        "status",
        "status_log",
        "study_encoding",
        "submitter",
        "trial_id",
    ],
) -> Dict[str, Tuple[Any, Any]]:
    """
    The actual comparison function that handles comparing values

    Handles formatting for date/time/datetime in CIDC
    Do not perform a comparison for ignored keys
    Add constant critical fields back to anything that changes
    """
    # handle formatting and ignore
    cidc1: Dict[str, Any] = {
        k: datetime.strftime(v, "%Y-%m-%d %H:%M:%S")
        if isinstance(v, (date, time, datetime))
        else v
        for k, v in cidc.items()
        if k not in ignore
    }
    csms1: Dict[str, Any] = {k: v for k, v in csms.items() if k not in ignore}

    # take difference by using symmetric set difference on the items
    # use set to not get same key multiple times if values differ
    diff_keys: Set[str] = {
        k
        for k in set(cidc1.keys()).union(set(csms1.keys()))
        # guaranteed to be in one or the other, so never None == None
        if cidc1.get(k) != csms1.get(k)
    }
    # then get both values once per key to return
    changes: Dict[str, Tuple[Any, Any]] = {
        k: (cidc.get(k), csms.get(k)) for k in diff_keys
    }

    return Change(
        entity_type=entity_type,
        trial_id=trial_id,
        manifest_id=manifest_id,
        cimac_id=csms["cimac_id"] if entity_type == "sample" else None,
        changes=changes,
    )


def _get_cidc_sample_map(metadata: dict) -> Dict[str, Dict[str, Any]]:
    """Returns a map of CIMAC IDs for this shipment to the relevant sample details from CIDC"""
    cidc_partic_map = {
        partic["cimac_participant_id"]: partic
        for partic in metadata.get("participants", [])
    }

    ## make maps from cimac_id to a full dict
    ## need to add participant-level values
    cidc_sample_map = {
        sample["cimac_id"]: sample
        for partic in metadata.get("participants", [])
        for sample in partic.get("samples", [])
    }
    for cidc_cimac_id in cidc_sample_map.keys():
        cimac_participant_id = cimac_id_to_cimac_participant_id(cidc_cimac_id, {})
        cidc_sample_map[cidc_cimac_id]["cohort_name"] = cidc_partic_map[
            cimac_participant_id
        ]["cohort_name"]
        cidc_sample_map[cidc_cimac_id]["participant_id"] = cidc_partic_map[
            cimac_participant_id
        ]["participant_id"]

    return cidc_sample_map


def _get_csms_sample_map(
    trial_id, manifest_id, csms_samples
) -> Dict[str, Dict[str, Any]]:
    """Returns a map of CIMAC IDs to the relevant sample details from CSMS"""
    return {
        csms_cimac_id: dict(
            # participant-level critical field
            cohort_name=csms_sample["cohort_name"],
            # name changes
            trial_id=csms_sample["protocol_identifier"],
            participant_id=csms_sample["participant_id"],
            # not in CSMS
            cimac_participant_id=cimac_id_to_cimac_participant_id(csms_cimac_id, {}),
            sample_manifest_type=csms_sample.get("sample_manifest_type"),
            # the rest of the values
            **_get_all_values(
                target="sample",
                old=csms_sample,
                drop=[
                    "cimac_participant_id",
                    "cohort_name",
                    "participant_id",
                    "sample_manifest_type",
                    "trial_id",
                ],
            ),
        )
        for csms_cimac_id, csms_sample in _convert_csms_samples(
            trial_id, manifest_id, csms_samples
        )
    }


def _cross_validate_samples(
    trial_id: str,
    manifest_id: str,
    cidc_sample_map: Dict[str, dict],
    csms_sample_map: Dict[str, dict],
    *,
    session: Session,
):
    # make sure that all of the CIDC samples are still in CSMS
    for cimac_id, cidc_sample in cidc_sample_map.items():
        if cimac_id not in csms_sample_map:
            formatted = (
                trial_id,
                manifest_id,
                cidc_sample["cimac_id"],
            )
            raise Exception(
                f"Missing sample: {formatted} on CSMS {(trial_id, manifest_id)}"
            )
    # make sure that all of the CSMS samples are in CIDC
    all_cidc_sample_map: Dict[str, dict] = {
        sample["cimac_id"]: {
            **sample,
            "trial_id": upload.trial_id,
            "manifest_id": upload.metadata_patch["shipments"][0]["manifest_id"],
        }
        for upload in session.query(UploadJobs)
        .filter(UploadJobs.status == UploadJobStatus.MERGE_COMPLETED.value)
        .all()
        for partic in upload.metadata_patch.get("participants", [])
        for sample in partic.get("samples", [])
        if len(upload.metadata_patch.get("shipments", []))
    }
    for cimac_id in csms_sample_map:
        # as sample maps are pulling only from CIDC for this trial_id / manifest_id
        # any missing cimac_id's are a change in critical field
        # but the cimac_id might exist elsewhere in CIDC
        if cimac_id not in cidc_sample_map:
            cidc_sample = all_cidc_sample_map.get(cimac_id, None)

            formatted = (
                (
                    cidc_sample["trial_id"],
                    cidc_sample["manifest_id"],
                    cidc_sample["cimac_id"],
                )
                if cidc_sample is not None
                else f"<no sample found>"
            )
            raise Exception(
                f"Change in critical field for: {formatted} to CSMS {(trial_id, manifest_id, cimac_id)}"
            )


def _initial_manifest_validation(
    csms_manifest: Dict[str, Any], *, session: Session
) -> Tuple[str, str, Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], UploadJobs]:
    """
    Gather all of the things we'll need while performing validation of the manifest

    Returns
    -------
    str : trial_id
    str : manifest_id
    Dict[str, Dict[str, Any]] : csms_sample_map
    Dict[str, Dict[str, Any]] : cidc_sample_map
        both map cimac_id's to a sample definition dict
    UploadJobs : cidc_uploadjob


    Exceptions Raised
    -----------------
    - "Cannot add a manifest that is not qc_complete"
        if manifest's status is not qc_complete (or null)
    - f"Manifest {manifest_id} contains no samples: {manifest}"
    - f"No consistent protocol_identifier defined for samples on manifest {manifest_id}"
    - f"Clinical trial with protocol identifier={trial_id} does not exist"
        if trial is missing from TrialMetadata
    - NewManifestError
        if there is no shipment with the given manifest_id
    - f"Change in critical field for: {(cidc.trial_id, cidc.manifest_id)} to CSMS {(trial_id, manifest_id)}"
        if the Shipment in CIDC has a different trial_id than in CSMS
    - f"Missing sample: {(cidc.trial_id, cidc.manifest_id, cidc.cimac_id)} on CSMS {(trial_id, manifest_id)}"
        if an sample in CIDC is not reflected in CSMS
    - f"Change in critical field for: {(cidc.trial_id, cidc.manifest_id, cidc.cimac_id)} to CSMS {(trial_id, manifest_id, cimac_id)}"
        if a sample in CSMS is not correctly reflected in the current state of CIDC
    - f"No assay_priority defined for manifest_id={manifest_id} for trial {trial_id}"
    - f"No assay_type defined for manifest_id={manifest_id} for trial {trial_id}"
    """
    trial_id, manifest_id, csms_samples = _extract_info_from_manifest(csms_manifest)
    # ----- Get all our information together -----
    # validate that trial exists in the JSON json or error otherwise
    _ = TrialMetadata.select_for_update_by_trial_id(trial_id, session=session)

    shipments: List[UploadJobs] = (
        session.query(UploadJobs)
        .filter(
            UploadJobs.status == UploadJobStatus.MERGE_COMPLETED.value,
            UploadJobs.trial_id == trial_id,
        )
        .all()
    )
    shipments_metadata: Dict[str, dict] = {
        s.metadata_patch["shipments"][0]["manifest_id"]: s
        for s in shipments
        if len(s.metadata_patch.get("shipments", []))
    }

    if manifest_id not in shipments_metadata:
        # remove this to allow for adding new manifests via this function
        # also need to uncomment new Sample code below
        raise NewManifestError()

    cidc_shipment: UploadJobs = shipments_metadata[manifest_id]

    cidc_sample_map = _get_cidc_sample_map(cidc_shipment.metadata_patch)
    csms_sample_map = _get_csms_sample_map(trial_id, manifest_id, csms_samples)

    # raises Exceptions if something is amiss
    _cross_validate_samples(
        trial_id=trial_id,
        manifest_id=manifest_id,
        cidc_sample_map=cidc_sample_map,
        csms_sample_map=csms_sample_map,
        session=session,
    )

    csms_assay_priority, csms_assay_type = _extract_details_from_trial(csms_samples)
    if csms_assay_priority:
        csms_manifest["assay_priority"] = csms_assay_priority
    if csms_assay_type:
        csms_manifest["assay_type"] = csms_assay_type

    return trial_id, manifest_id, csms_sample_map, cidc_sample_map, cidc_shipment


def _handle_shipment_differences(
    manifest_id: str,
    csms_manifest: Dict[str, Any],
    cidc_uploadjob: Optional[UploadJobs],
) -> Optional[Change]:
    """Compare the given CSMS and CIDC shipments, returning None's if no changes or the changes"""
    cidc_manifest: Dict[str, Any] = (
        {} if cidc_uploadjob is None else cidc_uploadjob.metadata_patch["shipments"][0]
    )
    change: Change = _calc_difference(
        entity_type="shipment",
        trial_id=cidc_uploadjob.trial_id,
        manifest_id=manifest_id,
        cidc=cidc_manifest,
        csms=csms_manifest,
        # default ignore
    )
    if change:
        return change
    else:
        return None


def _handle_sample_differences(
    trial_id: str,
    manifest_id: str,
    csms_sample_map: Dict[str, Dict[str, Any]],
    cidc_sample_map: Dict[str, Dict[str, Any]],
    ret: List[Change],
) -> List[Change]:
    """
    Compare the given CSMS and CIDC participants and samples

    Unlike _handle_shipment_differences and _handle_upload_differences,
    directly takes the return for detect_manifest_changes() and updates it
    before returning.
    No changes are made if no differences are found.
    """
    for cimac_id, csms_sample in csms_sample_map.items():
        change: Change = _calc_difference(
            entity_type="sample",
            trial_id=trial_id,
            manifest_id=manifest_id,
            cidc=cidc_sample_map[cimac_id],
            csms=csms_sample,
            # default ignore
        )
        if change:
            ret.append(change)

    return ret


def _handle_upload_differences(
    trial_id, manifest_id, csms_sample_map, uploader_email, cidc_uploadjob: UploadJobs
) -> Optional[Change]:
    """Look for the CIDC upload for the given manifest for changes, returning None's if no changes or the changes"""
    new_uploadjob = UploadJobs(
        trial_id=trial_id,
        _status=UploadJobStatus.MERGE_COMPLETED.value,
        multifile=False,
        upload_type=_get_upload_type(csms_sample_map.values()),
        uploader_email=uploader_email,
        metadata_patch={},
    )
    change: Change = _calc_difference(
        "upload",
        trial_id,
        manifest_id,
        {} if cidc_uploadjob is None else cidc_uploadjob.to_dict(),
        new_uploadjob.to_dict(),
        ignore=[
            "_created",
            "_etag",
            "id",
            "metadata_patch",
            "token",
            "_updated",
            "uploader_email",
        ],
    )
    if change:
        return change
    else:
        return None


@with_default_session
def detect_manifest_changes(
    csms_manifest: Dict[str, Any], uploader_email: str, *, session: Session
) -> List[Change]:
    """
    Given a CSMS-style manifest, see if it has any differences from the current state of the db
    If a new manifest, throws a NewManifestError
    If critical fields are different, throws an error to be handled later by a human
    Returns a list of the changes themselves

    Returns
    -------
    List[Change]
        the changes that were detected

    Raises
    ------
    NewManifestError
        if the manifest_id doesn't correspond to anything in CIDC
    Exception
        if the connections between any critical fields is changed
        namely trial_id, manifest_id, cimac_id
    """
    # if it's an excluded manifest, we don't consider it for changes
    if _get_and_check(
        obj=csms_manifest,
        key="excluded",
        default=False,
        msg=f"not called",
        check=lambda _: True,
    ):
        return []

    # ----- Initial validation, raises Exception if issues -----
    ret = []
    (
        trial_id,
        manifest_id,
        csms_sample_map,
        cidc_sample_map,
        cidc_uploadjob,
        # will raise NewManifestError if manifest_id not in Shipment table
    ) = _initial_manifest_validation(csms_manifest, session=session)

    # ----- Look for shipment-level differences -----
    change: Optional[Change] = _handle_shipment_differences(
        manifest_id, csms_manifest, cidc_uploadjob
    )
    if change:
        ret.append(change)

    # ----- Look for sample-level differences -----
    ret = _handle_sample_differences(
        trial_id, manifest_id, csms_sample_map, cidc_sample_map, ret
    )

    # ----- Look for differences in the Upload -----
    change: Optional[Change] = _handle_upload_differences(
        trial_id,
        manifest_id,
        csms_sample_map,
        uploader_email,
        cidc_uploadjob,
    )
    if change:
        ret.append(change)

    # ----- Finish up and return -----
    return ret
