from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
import time

import pytest

from builelib.input import parser
from builelib.input.parser import InputSheetParseResult, parse_input_sheet
from builelib.input.performance import calculate_wall_u_value, calculate_window_performance


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample01_WEBPRO_inputSheet_for_Ver3.8.xlsx"


def test_parse_input_sheet_returns_in_memory_result():
    result = parse_input_sheet(EXAMPLE)

    assert isinstance(result, InputSheetParseResult)
    assert len(result.data["AirHandlingSystem"]) == 26
    assert result.data["AirHandlingSystem"]["FCU1-1"]["Pump_cooling"] == "CHP2"
    assert result.data["AirHandlingSystem"]["FCU1-1"]["HeatSource_cooling"] == "AR1"
    lobby_shaded_wall = result.data["EnvelopeSet"]["1F_ロビー"]["WallList"][1]
    assert lobby_shaded_wall["Direction"] == "北"
    assert lobby_shaded_wall["WallType"] == "地盤に接する外壁"
    assert lobby_shaded_wall["OriginalWallType"] == "日の当たらない外壁"


def test_parse_input_sheet_rejects_unsupported_suffix(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError):
        parse_input_sheet(path)


def test_public_parser_serializes_legacy_calls(monkeypatch, tmp_path):
    paths = [tmp_path / f"{index}.xlsx" for index in range(2)]
    for path in paths:
        path.touch()

    state_lock = Lock()
    active = 0
    max_active = 0

    def fake_parser(_path):
        nonlocal active, max_active
        with state_lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.03)
        with state_lock:
            active -= 1
        return {"value": _path}, {"error": [], "warning": []}

    monkeypatch.setattr(parser, "make_jsondata_from_Ver2_sheet", fake_parser)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(parse_input_sheet, paths))

    assert max_active == 1
    assert len(results) == 2


def test_calculate_wall_u_value_from_layers():
    config = {
        "inputMethod": "建材構成を入力",
        "layers": [
            {"materialID": "test", "conductivity": 0.04, "thickness": 100.0},
            {"materialID": "air", "conductivity": None, "thickness": 0.0},
        ],
    }
    database = {"air": {"熱抵抗値": 0.1}}

    assert calculate_wall_u_value(config, database=database) == pytest.approx(1 / 2.75)


def test_calculate_window_performance_from_glass_type():
    config = {
        "inputMethod": "ガラスの種類を入力",
        "glassID": "G",
        "frameType": "金属製",
        "layerType": "単層",
    }
    glass = {"G": {"ガラス単体": {"熱貫流率": 6.0, "日射熱取得率": 0.8}}}
    conversion = {"金属製建具": {"単層": {"ku_a": 0.8, "ku_b": 1.0, "kita": 0.75}}}

    assert calculate_window_performance(
        config,
        glass_database=glass,
        conversion_database=conversion,
    ) == pytest.approx((5.8, 0.6))
