from pathlib import Path

import pytest

from ingest.licence import LicenceValidationError, load_sources


def test_sources_yaml_has_licence_on_every_record():
    path = Path("collections/complex-systems/sources.yaml")
    records = load_sources(str(path))
    assert len(records) == 46


def test_missing_licence_raises():
    from ingest.licence import SourceRecord

    rec = SourceRecord(
        id="x",
        title="t",
        authors=[],
        year=None,
        url="https://example.com",
        licence="",
        licence_url="",
        licence_class="A",
        nc_flag=False,
        nd_flag=False,
        attribution_text="",
        format="html",
    )
    with pytest.raises(LicenceValidationError):
        rec.validate()
