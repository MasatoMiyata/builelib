"""室・空調ゾーンの対応、既存JSON互換性、照明連成の回帰テスト。"""

import copy
import json
from pathlib import Path

import numpy as np
import pytest
from openpyxl import Workbook, load_workbook

from builelib import commons
from builelib.input.air_conditioning_zones import zone_properties, lighting_heat_density
from builelib.input.make_inputdata import make_jsondata_from_Ver2_sheet
from builelib.input.parser import parse_input_sheet
from builelib.input.reference_specification import prepare_input_data, expand_reference_specifications
from builelib.runner import calculate_from_json
from builelib.systems import airconditioning, other_energy


ROOT = Path(__file__).resolve().parents[1]


def _original():
    return json.loads((ROOT / "tests/airconditioning/ACtest_Case001.json").read_text(encoding="utf-8"))


def _renamed(data, grouped=False):
    result = copy.deepcopy(data)
    original_key = next(iter(result["AirConditioningZone"]))
    new_key = "1F_zone"
    zone = result["AirConditioningZone"].pop(original_key)
    zone["roomKeys"] = [original_key]
    if grouped:
        room = result["Rooms"][original_key]
        annex = copy.deepcopy(room)
        annex["roomArea"] = room["roomArea"] * 0.6
        room["roomArea"] *= 0.4
        result["Rooms"]["1F_annex"] = annex
        zone["roomKeys"].append("1F_annex")
    result["AirConditioningZone"][new_key] = zone
    result["EnvelopeSet"][new_key] = result["EnvelopeSet"].pop(original_key)
    return result, original_key, new_key


@pytest.mark.parametrize("grouped", [False, True])
def test_old_json_and_explicit_membership_have_identical_energy_and_loads(grouped):
    original = _original()
    changed, old_key, new_key = _renamed(original, grouped)
    before = copy.deepcopy(changed)
    prepared, validation = prepare_input_data(changed, validate_schema=False)
    assert validation["error"] == []
    assert changed == before  # 検証でRoomsや既存JSONを変更しない。
    expected = airconditioning.calc_energy(copy.deepcopy(original))
    actual = airconditioning.calc_energy(copy.deepcopy(prepared))
    for key in ("設計一次エネルギー消費量[MJ/年]", "基準一次エネルギー消費量[MJ/年]", "BEI/AC", "計算対象面積"):
        assert actual[key] == pytest.approx(expected[key], rel=1e-12)
    for key in ("年間室負荷（冷房）[MJ]", "年間室負荷（暖房）[MJ]"):
        np.testing.assert_allclose(actual["Qroom"][new_key][key], expected["Qroom"][old_key][key])
    expected_other = other_energy.calc_energy(copy.deepcopy(original))
    actual_other = other_energy.calc_energy(copy.deepcopy(changed))
    assert actual_other["E_other"] == pytest.approx(expected_other["E_other"])
    np.testing.assert_allclose(actual_other["for_CGS"]["ratio_AreaWeightedSchedule_AC"], expected_other["for_CGS"]["ratio_AreaWeightedSchedule_AC"])


def _lighting(power):
    return {"lightingUnit": {"L1": {"RatedPower": power, "Number": 1,
        "OccupantSensingCTRL": "有", "IlluminanceSensingCTRL": "有"}}}


@pytest.mark.parametrize("input_kind", ["missing", "partial", "all", "zero"])
def test_coupled_lighting_sums_rooms_and_uses_standard_for_missing_rooms(input_kind):
    source, first, zone = _renamed(_original(), grouped=True)
    source["CalculationMode"]["空調と照明の連成計算"] = True
    standard, *_ = commons.get_roomHeatGain("事務所等", "事務室", json.loads(
        (ROOT / "src/builelib/database/common_room_usage_schedule.json").read_text(encoding="utf-8")))
    if input_kind in ("partial", "all", "zero"):
        source["LightingSystems"][first] = _lighting(0 if input_kind == "zero" else 600)
    if input_kind == "all":
        source["LightingSystems"]["1F_annex"] = _lighting(900)
    first_power = standard * 80 if input_kind == "missing" else (0 if input_kind == "zero" else 600)
    second_power = 900 if input_kind == "all" else standard * 120
    assert lighting_heat_density(source, zone, standard) == pytest.approx((first_power + second_power) / 200)

    # 1室で同じ総電力を与えた計算と、合算後の負荷・年間エネルギーを比較する。
    equivalent = _original()
    old_key = next(iter(equivalent["Rooms"]))
    equivalent["CalculationMode"]["空調と照明の連成計算"] = True
    equivalent["LightingSystems"][old_key] = _lighting(first_power + second_power)
    expected = airconditioning.calc_energy(equivalent)
    actual = airconditioning.calc_energy(source)
    assert actual["設計一次エネルギー消費量[MJ/年]"] == pytest.approx(expected["設計一次エネルギー消費量[MJ/年]"])
    assert actual["Qroom"][zone]["年間室負荷（冷房）[MJ]"] == pytest.approx(expected["Qroom"][old_key]["年間室負荷（冷房）[MJ]"])


def test_missing_lighting_on_legacy_json_keeps_standard_heat_gain():
    source = _original()
    standard = airconditioning.calc_energy(copy.deepcopy(source))
    source["CalculationMode"]["空調と照明の連成計算"] = True
    coupled = airconditioning.calc_energy(source)
    assert coupled["設計一次エネルギー消費量[MJ/年]"] == standard["設計一次エネルギー消費量[MJ/年]"]


@pytest.mark.parametrize("grouped", [False, True])
def test_excel_membership_keeps_envelope_and_same_name_json_unchanged(tmp_path, grouped):
    path = ROOT / "examples/WEBPRO/sample01_WEBPRO_inputSheet_for_Ver3.8.xlsx"
    original = parse_input_sheet(path)
    assert original.errors == []
    assert all("roomKeys" not in zone for zone in original.data["AirConditioningZone"].values())
    workbook = load_workbook(path, data_only=True)
    form1 = workbook["1) 室仕様"]
    zones = workbook["2-1) 空調ゾーン"]
    old_name = zones["B11"].value
    floor = zones["A11"].value
    old_key = f"{floor}_{old_name}"
    zones["I11"] = "new_zone"
    new_key = f"{floor}_new_zone"
    if grouped:
        row = next(row for row in form1.iter_rows(min_row=11) if row[0].value == floor and row[1].value == old_name)
        values = [cell.value for cell in row]
        area_index = 5 if str(form1["A1"].value).endswith("Rev.2") else 4
        area = float(values[area_index])
        row[area_index].value = area * 0.4
        values[1], values[area_index] = "annex", area * 0.6
        form1.append(values)
        member = [zones.cell(11, col).value for col in range(1, 8)]
        member[1], member[4] = "annex", area * 0.6
        zones["E11"] = area * 0.4
        zones.insert_rows(12)
        for column, value in enumerate(member, 1):
            zones.cell(12, column, value)
    for row in workbook["2-4) 外皮 "].iter_rows(min_row=11):
        if row[0].value == floor and row[1].value == old_name:
            row[1].value = "new_zone"
    output = tmp_path / "zones.xlsx"
    workbook.save(output)
    parsed = parse_input_sheet(output)
    assert parsed.errors == []
    expected_members = [old_key] + ([f"{floor}_annex"] if grouped else [])
    assert parsed.data["AirConditioningZone"][new_key]["roomKeys"] == expected_members
    assert parsed.data["EnvelopeSet"][new_key] == original.data["EnvelopeSet"][old_key]
    assert zone_properties(parsed.data, new_key)["zoneArea"] == pytest.approx(original.data["Rooms"][old_key]["roomArea"])


def _small_workbook(tmp_path, second_type="事務室", second_ahu=None):
    workbook = Workbook()
    rooms = workbook.active
    rooms.title = "F1"
    rooms["A1"] = "F1"
    rooms["M2"] = "column bound"
    zones = workbook.create_sheet("F2-1")
    zones["L2"] = "column bound"
    for row, (name, room_type) in enumerate((("A", "事務室"), ("B", second_type)), 11):
        for column, value in enumerate(("1F", name, "事務所等", room_type, 50, 3, 2.7), 1):
            rooms.cell(row, column, value)
        zones.cell(row, 1, "1F")
        zones.cell(row, 2, name)
    for column, value in ((8, "1F"), (9, "Z"), (10, "AHU"), (11, "AHU")):
        zones.cell(11, column, value)
    if second_ahu:
        zones.cell(12, 10, second_ahu)
    path = tmp_path / "input.xlsx"
    workbook.save(path)
    return path


@pytest.mark.parametrize("room_type, ahu, expected", [("会議室", None, "建物用途・室用途"), ("事務室", "other", "空調機群名称")])
def test_excel_inconsistent_members_report_source_rows(tmp_path, room_type, ahu, expected):
    raw, validation = make_jsondata_from_Ver2_sheet(str(_small_workbook(tmp_path, room_type, ahu)))
    assert any("F2-1" in error and "12行目" in error and expected in error for error in validation["error"])
    _, prepared_validation = prepare_input_data(raw, validation, from_excel=True, validate_schema=False)
    assert prepared_validation["error"] == validation["error"]


@pytest.mark.parametrize("bad_keys", [[], "room", ["missing"], [None], ["1F_annex", "1F_annex"]])
def test_invalid_json_membership_stops_before_calculation(bad_keys, monkeypatch):
    source, _, zone = _renamed(_original(), grouped=True)
    source["AirConditioningZone"][zone]["roomKeys"] = bad_keys
    def should_not_run(*args, **kwargs):
        pytest.fail("不正な所属情報で計算が開始された")
    monkeypatch.setattr(airconditioning, "calc_energy", should_not_run)
    calculation = calculate_from_json(source)
    assert any("AirConditioningZone -> 1F_zone" in error for error in calculation["errors"])


def test_explicit_room_keys_take_priority_over_same_named_unrelated_room():
    source, first, zone = _renamed(_original())
    source["Rooms"][zone] = {**source["Rooms"][first], "roomArea": 999}
    assert zone_properties(source, zone)["zoneArea"] == 200


def test_schema_keeps_legacy_json_and_accepts_optional_room_keys():
    original = _original()
    assert commons.inputdata_validation(original) == []
    changed, _, zone = _renamed(original, grouped=True)
    assert commons.inputdata_validation(changed) == []
    changed["AirConditioningZone"][zone]["roomKeys"] = []
    assert any("roomKeys" in error for error in commons.inputdata_validation(changed))


@pytest.mark.parametrize("invalid", ["usage", "area", "duplicate_owner", "envelope", "implicit_missing"])
def test_shared_validation_reports_invalid_relationships(invalid):
    source, first, zone = _renamed(_original(), grouped=True)
    if invalid == "usage":
        source["Rooms"]["1F_annex"]["roomType"] = "会議室"
    elif invalid == "area":
        source["Rooms"]["1F_annex"]["roomArea"] = 0
    elif invalid == "duplicate_owner":
        source["AirConditioningZone"]["second"] = {**source["AirConditioningZone"][zone], "roomKeys": [first]}
    elif invalid == "envelope":
        source["EnvelopeSet"]["missing"] = source["EnvelopeSet"].pop(zone)
    else:
        source["AirConditioningZone"][zone].pop("roomKeys")
    _, validation = prepare_input_data(source, validate_schema=False)
    assert validation["error"]


@pytest.mark.parametrize("conditioned", ["無", "有", None], ids=["unconditioned", "conditioned", "unspecified"])
def test_envelope_reference_check_excludes_only_explicitly_unconditioned_envelopes(conditioned):
    source = _original()
    original_zone = next(iter(source["EnvelopeSet"]))
    envelope = copy.deepcopy(source["EnvelopeSet"][original_zone])
    if conditioned is None:
        envelope.pop("isAirconditioned", None)
    else:
        envelope["isAirconditioned"] = conditioned
    source["EnvelopeSet"]["1F_non_ac"] = envelope

    _, validation = prepare_input_data(source)

    if conditioned == "無":
        assert validation["error"] == []
    else:
        assert any("EnvelopeSet -> 1F_non_ac" in error for error in validation["error"])


def test_legacy_json_with_unconditioned_envelope_keeps_calculation_results():
    source = _original()
    original_zone = next(iter(source["AirConditioningZone"]))
    source["Rooms"]["1F_non_ac"] = {**source["Rooms"][original_zone], "roomArea": 10}
    expected = calculate_from_json(copy.deepcopy(source))
    source["EnvelopeSet"]["1F_non_ac"] = {
        **copy.deepcopy(source["EnvelopeSet"][original_zone]), "isAirconditioned": "無",
    }

    actual = calculate_from_json(source)

    assert actual["errors"] == expected["errors"] == []
    assert actual["result"] == expected["result"]


def test_reference_specifications_use_combined_area_and_member_usage():
    original = _original()
    old_zone = next(iter(original["AirConditioningZone"]))
    for field in ("AHU_cooling_insideLoad", "AHU_cooling_outdoorLoad", "AHU_heating_insideLoad", "AHU_heating_outdoorLoad"):
        original["AirConditioningZone"][old_zone][field] = "基準設定仕様"
    original["ReferenceSpecificationRequests"] = [{"equipment": "空調機群", "zone": old_zone}]
    wall = original["EnvelopeSet"][old_zone]["WallList"][0]
    wall["WallSpec"] = "基準設定仕様"
    original["ReferenceSpecificationRequests"].append({"equipment": "外壁", "zone": old_zone, "wallIndex": 0})
    changed, _, new_zone = _renamed(original, grouped=True)
    for request in changed["ReferenceSpecificationRequests"]:
        request["zone"] = new_zone
    expected, errors = expand_reference_specifications(original)
    assert errors == []
    actual, errors = expand_reference_specifications(changed)
    assert errors == []
    for section in ("AirHandlingSystem", "HeatsourceSystem", "SecondaryPumpSystem", "WallConfigure"):
        assert actual[section] == expected[section]


@pytest.mark.parametrize("read_error", [False, True])
def test_invalid_membership_is_checked_before_reference_expansion(monkeypatch, read_error):
    from builelib.input import reference_specification

    source, _, zone = _renamed(_original())
    if not read_error:
        source["AirConditioningZone"][zone]["roomKeys"] = ["missing"]
    source["ReferenceSpecificationRequests"] = [{"equipment": "空調機群", "zone": zone}]
    def should_not_expand(*args, **kwargs):
        pytest.fail("所属室の検証より先に設備が生成された")
    monkeypatch.setattr(reference_specification, "expand_reference_specifications", should_not_expand)
    previous = {"error": [f"F2-1 12行目: AirConditioningZone -> {zone}: 空調機群名称が一致しません。"]} if read_error else None
    _, validation = prepare_input_data(source, previous)
    assert validation["error"]


def test_json_calculation_entry_point_accepts_combined_zone():
    expected = calculate_from_json(_original())
    source, _, _ = _renamed(_original(), grouped=True)
    actual = calculate_from_json(source)
    assert actual["errors"] == expected["errors"] == []
    for key, value in expected["result"].items():
        if isinstance(value, (float, int)):
            assert actual["result"][key] == pytest.approx(value)
        else:
            assert actual["result"][key] == value
