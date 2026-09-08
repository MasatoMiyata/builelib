import json
from pathlib import Path

from builelib.commons import inputdata_validation


SAMPLE_PATH = (
    Path(__file__).parent
    / "whole_building"
    / "Builelib_inputSheet_sample_001.json"
)


def _sample_inputdata():
    with SAMPLE_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def test_schema_validation_can_skip_errors_for_empty_excel_values():
    inputdata = _sample_inputdata()
    inputdata["Building"]["Region"] = ""
    inputdata["Building"]["BuildingFloorArea"] = ""

    errors = inputdata_validation(inputdata, skip_empty_values=True)

    assert not any("Building -> Region" in error for error in errors)
    assert not any("Building -> BuildingFloorArea" in error for error in errors)


def test_schema_validation_reports_empty_values_by_default():
    inputdata = _sample_inputdata()
    inputdata["Building"]["Region"] = ""

    errors = inputdata_validation(inputdata)

    assert any("Building -> Region" in error for error in errors)


def test_skipping_empty_values_keeps_nonempty_schema_errors():
    inputdata = _sample_inputdata()
    inputdata["Building"]["Region"] = "invalid"

    errors = inputdata_validation(inputdata, skip_empty_values=True)

    assert any("Building -> Region" in error for error in errors)
