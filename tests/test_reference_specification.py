"""???????Excel?JSON?????????????"""

import copy
import json
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from builelib import commons
from builelib.input.make_inputdata import make_jsondata_from_Ver2_sheet
from builelib.input.parser import parse_input_sheet
from builelib.input.reference_specification import expand_reference_specifications, lighting_rated_power


def _workbook(tmp_path, rooms, lighting_rows):
    workbook = Workbook()
    form1 = workbook.active
    form1.title = "F1"
    form1["A1"] = "F1"
    form1["M2"] = "column bound"
    form4 = workbook.create_sheet("F4")
    for row_number, (name, building, room_type, area) in enumerate(rooms, start=11):
        for column, value in enumerate(("1F", name, building, room_type, area), start=1):
            form1.cell(row_number, column, value)
    for row_number, row in enumerate(lighting_rows, start=11):
        for column, value in row.items():
            form4.cell(row_number, column, value)
    # The legacy parser reads fixed columns through Q, including on continuation rows.
    form4["Q1"] = ""
    form4["Q2"] = "column bound"
    path = tmp_path / "lighting.xlsx"
    workbook.save(path)
    return path


def test_reference_lighting_expands_base_and_continuation_rows(tmp_path):
    path = _workbook(
        tmp_path,
        [("R1", "事務所等", "事務室", 100), ("R2", "事務所等", "事務室", 25)],
        [
            {1: "1F", 2: "R1", 5: 0, 11: "基準設定仕様", 12: 999, 13: 3, 14: "有"},
            {11: "基準設定仕様"},
            {1: "1F", 2: "R2", 5: 25, 11: "基準設定仕様_照明_0001", 12: 10, 13: 2},
        ],
    )
    parsed = parse_input_sheet(path)
    assert not [error for error in parsed.errors if "基準設定仕様" in error]
    units = parsed.data["LightingSystems"]["1F_R1"]["lightingUnit"]
    assert list(units) == ["基準設定仕様_照明_0002", "基準設定仕様_照明_0003"]
    for unit in units.values():
        assert unit == {
            "RatedPower": 1630,
            "Number": 1,
            "OccupantSensingCTRL": "無",
            "IlluminanceSensingCTRL": "無",
            "TimeScheduleCTRL": "無",
            "InitialIlluminationCorrectionCTRL": "無",
        }
    assert parsed.data["LightingSystems"]["1F_R2"]["lightingUnit"]["基準設定仕様_照明_0001"]["RatedPower"] == 10


def test_excel_reader_keeps_reference_request_for_calculation_stage(tmp_path):
    path = _workbook(
        tmp_path,
        [("R1", "事務所等", "事務室", 100)],
        [{1: "1F", 2: "R1", 11: "基準設定仕様"}],
    )

    raw, validation = make_jsondata_from_Ver2_sheet(str(path))
    assert not [error for error in validation["error"] if "基準設定仕様" in error]
    assert not [error for error in validation["error"] if "スキーマエラー" in error]
    assert raw["LightingSystems"]["1F_R1"]["lightingUnit"] == {}
    assert raw["ReferenceSpecificationRequests"] == [
        {"equipment": "照明", "room": "1F_R1", "source": "F4 11行目（機器名称）"}
    ]

    from builelib.input.reference_specification import prepare_input_data

    complete, result_validation = prepare_input_data(raw, validation, from_excel=True)
    assert not [error for error in result_validation["error"] if "基準設定仕様" in error]
    assert "ReferenceSpecificationRequests" not in complete
    assert complete["LightingSystems"]["1F_R1"]["lightingUnit"]["基準設定仕様_照明_0001"]["RatedPower"] == 1630


def test_excel_runner_writes_expanded_input(tmp_path):
    from builelib import runner

    path = _workbook(
        tmp_path,
        [("R1", "事務所等", "事務室", 100)],
        [{1: "1F", 2: "R1", 11: "基準設定仕様"}],
    )
    runner.calculate(path, exec_calculation=False)

    output = json.loads((tmp_path / "lighting_input.json").read_text(encoding="utf-8"))
    assert "ReferenceSpecificationRequests" not in output
    assert output["LightingSystems"]["1F_R1"]["lightingUnit"]["基準設定仕様_照明_0001"]["RatedPower"] == 1630


def test_excel_runner_reports_reference_error_with_sheet_row(tmp_path):
    from builelib import runner

    path = _workbook(
        tmp_path,
        [("R1", "共同住宅", "住戸", 100)],
        [{1: "1F", 2: "R1", 11: "基準設定仕様"}],
    )
    runner.calculate(path, exec_calculation=False)

    validation = json.loads((tmp_path / "lighting_validation.json").read_text(encoding="utf-8"))
    assert any("F4 11行目" in error and "共同住宅" in error for error in validation["error"])


def test_reference_lighting_rejects_unsupported_and_bad_area(tmp_path):
    path = _workbook(
        tmp_path,
        [("R1", "共同住宅", "住戸", 30), ("R2", "事務所等", "事務室", 0)],
        [
            {1: "1F", 2: "R1", 5: 30, 11: "基準設定仕様"},
            {1: "1F", 2: "R2", 5: 20, 11: "基準設定仕様"},
        ],
    )
    parsed = parse_input_sheet(path)
    assert any("F4 11行目" in error and "共同住宅" in error and "対象外" in error for error in parsed.errors)
    assert any("F4 12行目" in error and "床面積" in error and "正の数値" in error for error in parsed.errors)
    assert "1F_R1" not in parsed.data["LightingSystems"]
    assert "1F_R2" not in parsed.data["LightingSystems"]


def test_reference_lighting_rejects_missing_database_value(monkeypatch):
    from builelib.input import reference_specification as reference

    source = reference._load_database()
    database = json.loads(json.dumps(source))
    database["ventilation_and_lighting"]["rooms"]["事務所等"]["事務室"]["lighting"]["基準設定消費電力 [W/m2]"] = None
    monkeypatch.setattr(reference, "_load_database", lambda: database)
    try:
        lighting_rated_power("事務所等", "事務室", 100)
    except reference.ReferenceSpecificationError as exc:
        assert "適用できません" in str(exc)
    else:
        raise AssertionError("Missing reference power was accepted")


def test_json_requests_use_same_expansion_without_changing_source():
    source = {
        "Rooms": {
            "1F_R1": {"buildingType": "事務所等", "roomType": "事務室", "roomArea": 100},
        },
        "LightingSystems": {
            "1F_R1": {"roomIndex": 2.5, "lightingUnit": {"基準設定仕様_照明_0001": {"RatedPower": 10}}},
        },
        "ReferenceSpecificationRequests": [
            {"equipment": "照明", "room": "1F_R1"},
            {"equipment": "照明", "room": "1F_R1"},
        ],
    }
    original = copy.deepcopy(source)
    expanded, errors = expand_reference_specifications(source)
    assert errors == []
    assert source == original
    assert "ReferenceSpecificationRequests" not in expanded
    units = expanded["LightingSystems"]["1F_R1"]["lightingUnit"]
    assert list(units) == [
        "基準設定仕様_照明_0001",
        "基準設定仕様_照明_0002",
        "基準設定仕様_照明_0003",
    ]
    assert units["基準設定仕様_照明_0002"]["RatedPower"] == 1630
    assert expanded["LightingSystems"]["1F_R1"]["roomWidth"] is None


def test_json_lighting_request_rejects_area_override():
    source = {
        "Rooms": {
            "1F_R1": {"buildingType": "事務所等", "roomType": "事務室", "roomArea": 100},
        },
        "ReferenceSpecificationRequests": [
            {"equipment": "照明", "room": "1F_R1", "roomArea": 20},
        ],
    }
    _, errors = expand_reference_specifications(source)
    assert any("roomArea" in error for error in errors)


def test_json_requests_report_unsupported_building():
    source = {
        "Rooms": {"1F_R1": {"buildingType": "共同住宅", "roomType": "住戸", "roomArea": 30}},
        "ReferenceSpecificationRequests": [{"equipment": "照明", "room": "1F_R1"}],
    }
    expanded, errors = expand_reference_specifications(source)
    assert any("共同住宅" in error and "対象外" in error for error in errors)
    assert "1F_R1" not in expanded["LightingSystems"]


def test_calculate_from_json_expands_before_lighting_calculation(monkeypatch):
    from builelib import runner

    seen = {}

    def fake_lighting(inputdata, **kwargs):
        seen["units"] = inputdata["LightingSystems"]["1F_R1"]["lightingUnit"]
        return {"for_CGS": {}, "E_lighting": 10, "Es_lighting": 20, "BEI_L": 0.5}

    monkeypatch.setattr(runner.bc, "inputdata_validation", lambda data: [])
    monkeypatch.setattr(runner.lighting, "calc_energy", fake_lighting)
    monkeypatch.setattr(runner.other_energy, "calc_energy", lambda *args, **kwargs: {"for_CGS": {}, "E_other": 0})
    source = {
        "Rooms": {"1F_R1": {"buildingType": "事務所等", "roomType": "事務室", "roomArea": 100}},
        "ReferenceSpecificationRequests": [{"equipment": "照明", "room": "1F_R1"}],
    }
    result = runner.calculate_from_json(source)
    assert result["errors"] == []
    assert seen["units"]["基準設定仕様_照明_0001"]["RatedPower"] == 1630
    assert "LightingSystems" not in source


def test_calculate_from_json_stops_on_reference_error(monkeypatch):
    from builelib import runner

    def must_not_calculate(*args, **kwargs):
        raise AssertionError("入力エラー後に設備計算が呼ばれました")

    monkeypatch.setattr(runner.lighting, "calc_energy", must_not_calculate)
    source = {
        "Rooms": {"1F_R1": {"buildingType": "共同住宅", "roomType": "住戸", "roomArea": 30}},
        "ReferenceSpecificationRequests": [{"equipment": "照明", "room": "1F_R1"}],
    }
    result = runner.calculate_from_json(source)
    assert any("共同住宅" in error for error in result["errors"])


def test_json_file_input_uses_common_expansion(tmp_path, monkeypatch):
    from builelib import runner

    monkeypatch.setattr(runner.bc, "inputdata_validation", lambda data: [])
    source = {
        "Rooms": {"1F_R1": {"buildingType": "事務所等", "roomType": "事務室", "roomArea": 100}},
        "ReferenceSpecificationRequests": [{"equipment": "照明", "room": "1F_R1"}],
    }
    path = tmp_path / "input.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    runner.calculate(path, exec_calculation=False)
    expanded = json.loads((tmp_path / "input_input.json").read_text(encoding="utf-8"))
    validation = json.loads((tmp_path / "input_validation.json").read_text(encoding="utf-8"))
    assert validation["error"] == []
    assert expanded["LightingSystems"]["1F_R1"]["lightingUnit"]["基準設定仕様_照明_0001"]["RatedPower"] == 1630
    assert "ReferenceSpecificationRequests" not in expanded


def test_expanded_real_json_passes_input_schema():
    from builelib import commons

    example = Path(__file__).parent / "whole_building" / "sample01_WEBPRO_inputSheet_for_Ver3.8_input.json"
    source = json.loads(example.read_text(encoding="utf-8"))
    source["ReferenceSpecificationRequests"] = [{"equipment": "照明", "room": "1F_ロビー"}]
    expanded, errors = expand_reference_specifications(source)
    assert errors == []
    assert commons.inputdata_validation(expanded) == []


SAMPLE_JSON = Path(__file__).parent / "whole_building" / "sample01_WEBPRO_inputSheet_for_Ver3.8_input.json"
SAMPLE_XLSX = Path(__file__).parent / "whole_building" / "sample01_WEBPRO_inputSheet_for_Ver3.8.xlsx"


def _sample_with_requests():
    source = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    wall = source["EnvelopeSet"]["1F_ロビー"]["WallList"][0]
    wall["WallSpec"] = "基準設定仕様"
    wall["WindowList"][0]["WindowID"] = "基準設定仕様"
    source["ReferenceSpecificationRequests"] = [
        {"equipment": "外壁", "zone": "1F_ロビー", "wallIndex": 0},
        {"equipment": "窓", "zone": "1F_ロビー", "wallIndex": 0, "windowIndex": 0},
        {"equipment": "換気", "room": "1F_便所1", "unitType": "排気"},
        {"equipment": "給湯", "room": "1F_中央監視室・警備室", "savingSystem": "無"},
        {"equipment": "昇降機", "room": "7F_事務室1"},
    ]
    return source


def test_all_five_non_lighting_equipment_expand_to_valid_calculation_json():
    source = _sample_with_requests()
    expanded, errors = expand_reference_specifications(source)
    assert errors == []
    assert commons.inputdata_validation(expanded) == []
    assert "ReferenceSpecificationRequests" in source  # 元のJSONは変更しない。
    assert "ReferenceSpecificationRequests" not in expanded

    wall = expanded["EnvelopeSet"]["1F_ロビー"]["WallList"][0]
    assert wall["WallSpec"] == "基準設定仕様_外壁_0001"
    assert expanded["WallConfigure"][wall["WallSpec"]]["Uvalue"] > 0
    window = wall["WindowList"][0]
    assert window["WindowID"] == "基準設定仕様_窓_0001"
    assert window["isBlind"] == "無"
    assert expanded["WindowConfigure"][window["WindowID"]]["windowIvalue"] > 0

    fan = expanded["VentilationUnit"]["基準設定仕様_換気_0001"]
    assert fan["FanAirVolume"] == 40.5 * 33.28
    assert fan["MoterRatedPower"] == 0.010125 * 33.28
    assert expanded["VentilationRoom"]["1F_便所1"]["VentilationUnitRef"]["基準設定仕様_換気_0001"]["UnitType"] == "排気"

    hotwater = expanded["HotwaterSupplySystems"]["基準設定仕様_給湯_0001"]
    assert hotwater["HeatSourceUnit"][0]["RatedCapacity"] == 10
    assert hotwater["HeatSourceUnit"][0]["RatedFuelConsumption"] == 12.5
    assert hotwater["PipeSize"] == 40
    assert expanded["HotwaterRoom"]["1F_中央監視室・警備室"]["HotwaterSystem"][-1]["SystemName"] == "基準設定仕様_給湯_0001"

    elevator = expanded["Elevators"]["7F_事務室1"]["Elevator"][-1]
    assert elevator["ElevatorName"] == "基準設定仕様_昇降機_0001"
    assert (elevator["Number"], elevator["LoadLimit"], elevator["Velocity"]) == (2, 1150, 120)


def test_excel_markers_use_common_expansion(tmp_path):
    workbook = load_workbook(SAMPLE_XLSX)
    workbook["2-4) 外皮 "]["F11"] = "基準設定仕様"
    workbook["2-4) 外皮 "]["H11"] = "基準設定仕様"
    workbook["3-1) 換気室"]["G11"] = "基準設定仕様"
    workbook["3-1) 換気室"]["E11"] = 0  # 様式3-1の床面積は使用しない。
    workbook["5-1) 給湯室"]["H11"] = "基準設定仕様"
    elevator_sheet = workbook["6) 昇降機"]
    elevator_sheet["E11"] = "基準設定仕様"
    for column in "FGHIJ":
        elevator_sheet[f"{column}11"] = None
    path = tmp_path / "reference.xlsx"
    workbook.save(path)
    from builelib.input.make_inputdata import make_jsondata_from_Ver2_sheet

    raw, excel_validation = make_jsondata_from_Ver2_sheet(str(path))
    assert not [error for error in excel_validation["error"] if "基準設定仕様" in error]
    assert raw["EnvelopeSet"]["1F_ロビー"]["WallList"][0]["WallSpec"] == "基準設定仕様"
    raw_reference_elevators = [
        elevator
        for room in raw["Elevators"].values()
        for elevator in room["Elevator"]
        if elevator["ElevatorName"] == "基準設定仕様"
    ]
    assert len(raw_reference_elevators) == 1
    assert raw_reference_elevators[0]["Number"] is None
    assert {request["equipment"] for request in raw["ReferenceSpecificationRequests"]} >= {
        "外壁", "窓", "換気", "給湯", "昇降機"
    }
    for request in raw["ReferenceSpecificationRequests"]:
        assert "11行目" in request["source"]

    parsed = parse_input_sheet(path)
    assert parsed.errors == []
    wall = parsed.data["EnvelopeSet"]["1F_ロビー"]["WallList"][0]
    assert wall["WallSpec"].startswith("基準設定仕様_外壁_")
    assert wall["WindowList"][0]["WindowID"].startswith("基準設定仕様_窓_")
    assert "基準設定仕様_換気_0001" in parsed.data["VentilationUnit"]
    fan = parsed.data["VentilationUnit"]["基準設定仕様_換気_0001"]
    room_area = parsed.data["Rooms"]["1F_便所1"]["roomArea"]
    assert fan["FanAirVolume"] == 40.5 * room_area
    assert fan["MoterRatedPower"] == 0.010125 * room_area
    assert "基準設定仕様_給湯_0001" in parsed.data["HotwaterSupplySystems"]
    assert any(
        elevator["ElevatorName"].startswith("基準設定仕様_昇降機_")
        for room in parsed.data["Elevators"].values()
        for elevator in room["Elevator"]
    )


@pytest.mark.parametrize("window_name", ["G1", "基準設定仕様"])
def test_excel_window_area_checked_during_sheet_reading(tmp_path, window_name):
    from builelib.input.make_inputdata import make_jsondata_from_Ver2_sheet

    workbook = load_workbook(SAMPLE_XLSX)
    sheet = workbook["2-4) 外皮 "]
    sheet["G11"] = 10
    sheet["H11"] = window_name
    path = tmp_path / "window_area.xlsx"
    workbook.save(path)

    _, validation = make_jsondata_from_Ver2_sheet(str(path))
    area_errors = [error for error in validation["error"] if "窓面積が外皮面積よりも大き" in error]
    assert len(area_errors) == 1

    if window_name == "基準設定仕様":
        parsed = parse_input_sheet(path)
        assert len([error for error in parsed.errors if "窓面積が外皮面積よりも大き" in error]) == 1


def test_horizontal_wall_uses_roof_value_and_skips_existing_name():
    from builelib.input.reference_specification import _load_database

    source = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    wall = source["EnvelopeSet"]["1F_ロビー"]["WallList"][0]
    wall["Direction"] = "水平（下）"
    wall["WallSpec"] = "基準設定仕様"
    source["WallConfigure"]["基準設定仕様_外壁_0001"] = copy.deepcopy(source["WallConfigure"]["W1"])
    source["ReferenceSpecificationRequests"] = [{"equipment": "外壁", "zone": "1F_ロビー", "wallIndex": 0}]
    expanded, errors = expand_reference_specifications(source)
    assert errors == []
    assert expanded["EnvelopeSet"]["1F_ロビー"]["WallList"][0]["WallSpec"] == "基準設定仕様_外壁_0002"
    db = _load_database()
    region = int(source["Building"]["Region"])
    sheet = next(sheet for sheet in db["air_conditioning_by_region"].values() if region in sheet["regions"])
    expected = sheet["rooms"]["事務所等"]["ロビー"]["熱貫流率(屋根)"]
    assert expanded["WallConfigure"]["基準設定仕様_外壁_0002"]["Uvalue"] == expected


def test_non_applicable_ventilation_is_an_input_error():
    source = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    source["ReferenceSpecificationRequests"] = [{"equipment": "換気", "room": "1F_ロビー", "unitType": "排気"}]
    expanded, errors = expand_reference_specifications(source)
    assert any("換気仕様を適用できません" in error for error in errors)
    assert "基準設定仕様_換気_0001" not in expanded["VentilationUnit"]


def test_ventilation_request_uses_only_rooms_area():
    source = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    request = {"equipment": "換気", "room": "1F_便所1", "unitType": "排気"}
    source["ReferenceSpecificationRequests"] = [{**request, "roomArea": 20}]
    _, errors = expand_reference_specifications(source)
    assert any("roomArea" in error for error in errors)

    source["ReferenceSpecificationRequests"] = [request]
    source["Rooms"]["1F_便所1"]["roomArea"] = 0
    expanded, errors = expand_reference_specifications(source)
    assert any("床面積" in error and "正の数値" in error for error in errors)
    assert "基準設定仕様_換気_0001" not in expanded["VentilationUnit"]


def test_region_eight_hotwater_efficiency_and_joint_housing_exclusion():
    source = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    source["Building"]["Region"] = "8"
    source["ReferenceSpecificationRequests"] = [
        {"equipment": "給湯", "room": "1F_中央監視室・警備室", "savingSystem": "無"}
    ]
    expanded, errors = expand_reference_specifications(source)
    assert errors == []
    fuel = expanded["HotwaterSupplySystems"]["基準設定仕様_給湯_0001"]["HeatSourceUnit"][0]["RatedFuelConsumption"]
    assert fuel == 10 / 0.82

    source["Rooms"]["1F_中央監視室・警備室"]["buildingType"] = "共同住宅"
    _, errors = expand_reference_specifications(source)
    assert any("共同住宅" in error and "対象外" in error for error in errors)


def test_missing_window_database_value_reports_source_row(monkeypatch):
    from builelib.input import reference_specification as reference

    database = copy.deepcopy(reference._load_database())
    source = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    region = int(source["Building"]["Region"])
    sheet = next(sheet for sheet in database["air_conditioning_by_region"].values() if region in sheet["regions"])
    record = sheet["rooms"]["事務所等"]["ロビー"]
    record["熱貫流率(窓)"] = None
    monkeypatch.setattr(reference, "_load_database", lambda: database)
    window = source["EnvelopeSet"]["1F_ロビー"]["WallList"][0]["WindowList"][0]
    window["WindowID"] = "基準設定仕様"
    source["ReferenceSpecificationRequests"] = [
        {"equipment": "窓", "zone": "1F_ロビー", "wallIndex": 0, "windowIndex": 0}
    ]
    expanded, errors = expand_reference_specifications(source)
    assert any("熱貫流率(窓)" in error and f"{record['_source_row']}行目" in error for error in errors)
    assert "基準設定仕様_窓_0001" not in expanded["WindowConfigure"]


def test_malformed_json_request_returns_validation_error():
    source = _sample_with_requests()
    source["Rooms"]["1F_ロビー"]["buildingType"] = []
    _, errors = expand_reference_specifications(source)
    assert any("建物用途・室用途が不正" in error for error in errors)
