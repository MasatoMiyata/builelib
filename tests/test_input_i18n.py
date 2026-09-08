import pytest

from builelib.input.make_inputdata import (
    _is_sheet_header,
    _norm,
    _norm_roomtype,
    normalize_input,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Daytime", "昼"),
        ("Nighttime", "深夜"),
        ("All day", "終日"),
        ("昼", "昼"),
        ("夜", "深夜"),
        ("深夜", "深夜"),
        ("終日", "終日"),
    ],
)
def test_air_conditioning_hours_translation(value, expected):
    assert _norm(value, "common_air_conditioning_hours") == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Cooling", "冷房"),
        ("Heating", "暖房"),
        ("冷房", "冷房"),
        ("暖房", "暖房"),
    ],
)
def test_ac_operation_mode_translation(value, expected):
    assert _norm(value, "ac_operation_mode") == expected


@pytest.mark.parametrize(
    ("category", "value", "expected"),
    [
        ("ac_heat_source_fuel_type", "Electricity", "電力"),
        ("ac_heat_source_fuel_type", "Gas", "ガス"),
        ("ac_heat_source_fuel_type", "LPG", "液化石油ガス"),
        ("ac_heat_source_fuel_type", "Heavy oil", "重油"),
        ("ac_heat_source_fuel_type", "Kerosene", "灯油"),
        ("ac_heat_source_fuel_type", "Chilled water", "冷水"),
        ("ac_heat_source_fuel_type", "Hot water", "温水"),
        ("ac_heat_source_fuel_type", "Steam", "蒸気"),
        ("ac_heat_source_type", "Not required", "不要"),
        ("ac_heat_source_type", "Water", "水"),
        ("ac_heat_source_type", "Air", "空気"),
        ("ac_heat_source_type", "Ground type 1", "地盤1"),
        ("ac_heat_source_type", "Ground type F", "地盤F"),
        ("ac_heat_source_curve_type", "Capacity ratio", "能力比"),
        ("ac_heat_source_curve_type", "Input ratio", "入力比"),
        ("ac_heat_source_curve_type", "Part-load characteristics", "部分負荷特性"),
        (
            "ac_heat_source_curve_type",
            "Supply water temperature characteristics",
            "送水温度特性",
        ),
    ],
)
def test_ac_heat_source_input_translation(category, value, expected):
    assert _norm(value, category) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Turbo chiller", "ターボ冷凍機"),
        ("ターボ冷凍機", "ターボ冷凍機"),
        ("Custom Heat Source", "Custom Heat Source"),
        ("任意熱源A", "任意熱源A"),
    ],
)
def test_custom_heat_source_name_only_normalizes_known_presets(value, expected):
    assert _norm(value, "ac_heat_source_performance") == expected


@pytest.mark.parametrize(
    "value",
    [
        "カレンダー\nパターン名称",
        "Calendar Pattern Name",
        "Calendar\nPattern Name",
    ],
)
def test_sheet_header_matching_ignores_line_breaks(value):
    assert _is_sheet_header(
        value,
        "カレンダー\nパターン名称",
        "Calendar Pattern Name",
    )


@pytest.mark.parametrize(
    ("value", "labels"),
    [
        ("Heat Source Group Name", ("熱源群名称", "Heat Source Group Name")),
        (
            "Air-Conditioning Unit Group Name",
            ("空調機群名称", "Air-Conditioning Unit Group Name"),
        ),
        ("Floor", ("階", "Floor")),
        (
            "Air-Conditioning Zone Name",
            ("空調ゾーン名称", "Air-Conditioning Zone Name"),
        ),
        ("Room Load Type", ("室負荷の種類", "Room Load Type")),
        ("Opening Name", ("開口部名称", "Opening Name")),
    ],
)
def test_english_sheet_headers_are_recognized(value, labels):
    assert _is_sheet_header(value, *labels)


def test_data_name_is_not_recognized_as_sheet_header():
    assert not _is_sheet_header("AR1", "熱源群名称", "Heat Source Group Name")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Office room", "事務室"),
        ("事務室", "事務室"),
        ("Executive Lounge", "Executive Lounge"),
        ("役員ラウンジ", "役員ラウンジ"),
    ],
)
def test_custom_room_type_name_only_normalizes_known_presets(value, expected):
    assert _norm_roomtype(value, "事務所等") == expected


def test_normalize_input_translates_air_conditioning_hours():
    input_data = {
        "SpecialInputData": {
            "room_usage_condition": {
                "事務所等": {
                    "Custom room": {
                        "空調運転パターン": "Nighttime",
                    }
                }
            }
        }
    }

    normalize_input(input_data)

    condition = input_data["SpecialInputData"]["room_usage_condition"]["事務所等"]["Custom room"]
    assert condition["空調運転パターン"] == "深夜"
