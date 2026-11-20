"""runner が各設備の BEI を二重に切り上げないことのテスト。

各設備の計算モジュールは BEI を小数第2位に切り上げて返す。runner でもう一度切り上げると、
0.56 * 100 = 56.00000000000001 のような浮動小数点の誤差で 0.01 大きくなる（0.56 → 0.57）。
"""

import math

import pytest

from builelib import runner

# 2回切り上げると 0.01 大きくなる値（math.ceil(v * 100) / 100 != v）
VALUES = [0.07, 0.14, 0.28, 0.55, 0.56, 1.09, 1.1, 1.11, 1.12]


def test_values_change_if_ceiled_twice():
    # テストの前提: これらの値は、もう一度切り上げると 0.01 大きくなる
    assert all(math.ceil(v * 100) / 100 == pytest.approx(v + 0.01) for v in VALUES)


def _fake(result: dict):
    return lambda *args, **kwargs: {"for_CGS": {}, **result}


@pytest.mark.parametrize("value", VALUES)
def test_calculate_from_json_keeps_equipment_bei_from_modules(monkeypatch, value):
    monkeypatch.setattr(runner.database_loader, "load_all_databases", lambda: {})
    monkeypatch.setattr(runner.airconditioning, "calc_energy", _fake(
        {"設計一次エネルギー消費量[MJ/年]": 10, "基準一次エネルギー消費量[MJ/年]": 20, "BEI/AC": value}))
    monkeypatch.setattr(runner.ventilation, "calc_energy", _fake(
        {"設計一次エネルギー消費量[MJ/年]": 10, "基準一次エネルギー消費量[MJ/年]": 20, "BEI/V": value}))
    monkeypatch.setattr(runner.lighting, "calc_energy", _fake(
        {"E_lighting": 10, "Es_lighting": 20, "BEI_L": value}))
    monkeypatch.setattr(runner.hotwatersupply, "calc_energy", _fake(
        {"設計一次エネルギー消費量[MJ/年]": 10, "基準一次エネルギー消費量[MJ/年]": 20, "BEI/HW": value}))
    monkeypatch.setattr(runner.elevator, "calc_energy", _fake(
        {"E_elevator": 10, "Es_elevator": 20, "BEI_EV": value}))
    monkeypatch.setattr(runner.other_energy, "calc_energy", _fake({"E_other": 0}))
    source = {
        "Rooms": {"1F_R1": {}},
        "AirConditioningZone": {"1F_R1": {}},
        "VentilationRoom": {"1F_R1": {}},
        "LightingSystems": {"1F_R1": {}},
        "HotwaterRoom": {"1F_R1": {}},
        "Elevators": {"1F_R1": {}},
    }
    output = runner.calculate_from_json(source)
    assert output["errors"] == []
    result = output["result"]
    for key in ("BEI_AC", "BEI_V", "BEI_L", "BEI_HW", "BEI_EV"):
        assert result[key] == value, key
    # 建物全体の BEI は一次エネルギー消費量の合計から1回だけ切り上げる（50 / 100 = 0.5）
    assert result["BEI"] == 0.5
