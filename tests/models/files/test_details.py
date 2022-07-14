from cidc_api.models.files import details_dict
from cidc_api.models.files.details import FileDetails


def test_detail_dict():
    assert all(
        isinstance(k, str) and isinstance(v, FileDetails)
        for k, v in details_dict.items()
    )
