import os.path
from collections import OrderedDict
from typing import Dict, List
from unittest.mock import MagicMock

from cidc_api.models.templates import (
    in_single_transaction,
    MetadataModel,
    Participant,
    PbmcManifest,
    remove_record_batch,
    Sample,
    TEMPLATE_MAP,
)

from .utils import set_up_example_trial, setup_example
from .examples import EXAMPLE_DIR


def test_remove_record_batch(cidc_api, clean_db):
    inserted: Dict[type, List[MetadataModel]] = setup_example(clean_db, cidc_api)

    with cidc_api.app_context():
        assert clean_db.query(Sample).count() == 2
        assert remove_record_batch(inserted[Sample][1:]) == []
        assert clean_db.query(Sample).count() == 1

        errs = remove_record_batch(inserted[Participant])
        assert len(errs) == 1
        assert 'participants" violates foreign key' in str(errs[0])

        # hold_commit flushes instead, still throws error
        errs = remove_record_batch(inserted[Participant], hold_commit=True)
        assert len(errs) == 1
        assert 'participants" violates foreign key' in str(errs[0])

        # dry_run doesn't change anything even when it would be successful
        errs = remove_record_batch(inserted[Sample][:1], dry_run=True)
        assert len(errs) == 0
        assert clean_db.query(Sample).count() == 1

        # dry_run does flush to get errors
        errs = remove_record_batch(inserted[Participant], dry_run=True)
        assert len(errs) == 1
        assert 'participants" violates foreign key' in str(errs[0])

        # hold_commit flushes instead of commits
        actual_commit = clean_db.commit
        clean_db.commit = MagicMock()
        errs = remove_record_batch(inserted[Sample][:1], hold_commit=True)
        assert len(errs) == 0
        assert clean_db.query(Sample).count() == 0
        clean_db.commit.assert_not_called()
        clean_db.commit = actual_commit


def test_in_single_transaction_smoketest(cidc_api):
    session = MagicMock()
    func1, func2 = MagicMock(), MagicMock()
    func1.return_value, func2.return_value = [], []

    def func1_assert(**kwargs):
        func1.assert_called_once_with(**kwargs)
        return []

    def func2_assert(**kwargs):
        func2.assert_not_called()
        return []

    calls = OrderedDict()
    calls[func1] = {"foo": "bar"}
    calls[func1_assert] = {"foo": "bar"}
    calls[func2_assert] = {}
    calls[func2] = {}

    errs = in_single_transaction(calls, session=session)
    assert len(errs) == 0, "\n".join(str(e) for e in errs)

    func1.assert_called_once_with(foo="bar", session=session, hold_commit=True)
    func2.assert_called_once_with(session=session, hold_commit=True)
    session.commit.assert_called_once()
    session.flush.assert_called()

    func1.reset_mock()
    func2.reset_mock()
    session.flush.reset_mock()
    session.commit.reset_mock()

    session.commit.side_effect = Exception("foo")
    errs = in_single_transaction(calls, session=session)
    assert len(errs) == 1
    assert "foo" in str(errs[0])
    func1.assert_called_once_with(foo="bar", session=session, hold_commit=True)
    func2.assert_called_once_with(session=session, hold_commit=True)


def test_get_full_template_name():
    assert list(TEMPLATE_MAP.keys()) == [
        "hande",
        "wes_bam",
        "wes_fastq",
        "pbmc",
        "tissue_slide",
    ]


def test_error_handling(cidc_api, clean_db):
    with cidc_api.app_context():
        set_up_example_trial(clean_db, cidc_api)

        errors = PbmcManifest.read_and_insert(
            os.path.join(EXAMPLE_DIR, "broken", "pbmc_manifest.bad_date.xlsx")
        )
        assert len(errors) == 1
        assert "is not a valid date" in str(errors[0])

        errors = PbmcManifest.read_and_insert(
            os.path.join(EXAMPLE_DIR, "broken", "pbmc_manifest.bad_enum.xlsx")
        )
        assert len(errors) == 1
        assert "invalid input value" in str(errors[0])

        errors = PbmcManifest.read_and_insert(
            os.path.join(EXAMPLE_DIR, "broken", "pbmc_manifest.bad_type.xlsx")
        )
        assert len(errors) == 1
        assert "invalid literal for int()" in str(errors[0])

        errors = PbmcManifest.read_and_insert(
            os.path.join(EXAMPLE_DIR, "broken", "pbmc_manifest.foreign_key.xlsx")
        )
        assert len(errors) == 1, "\n".join(str(e) for e in errors)
        assert "no Clinical Trial with trial_id" in str(
            errors[0]
        ) or "no Cohort with trial_id, cohort_name" in str(errors[0])

        errors = PbmcManifest.read_and_insert(
            os.path.join(EXAMPLE_DIR, "broken", "pbmc_manifest.not_null.xlsx")
        )
        assert len(errors) == 1
        assert "Missing required value" in str(errors[0])
