import pytest

from builelib.input.make_inputdata import _norm, normalize_input


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
