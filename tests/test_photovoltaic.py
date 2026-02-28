import pytest
from pathlib import Path
from builelib.input.make_inputdata import make_jsondata_from_Ver2_sheet
from builelib.systems import photovoltaic

# テストケースファイルのディレクトリ
TEST_DATA_DIR = Path(__file__).parent / "photovoltaic"

# 期待値（基準実装による計算値）
# E_photovoltaic: 全太陽光発電システムの年間一次エネルギー換算発電量 [MJ/年]
# （19システム × 各傾斜角0°〜180°、各9kW）
EXPECTED_E_PV = 909994.5203062877


@pytest.fixture
def pv_inputdata():
    xlsm_path = TEST_DATA_DIR / "PV_case01.xlsm"
    inputdata, _ = make_jsondata_from_Ver2_sheet(str(xlsm_path))
    inputdata.setdefault("SpecialInputData", {})
    return inputdata


def test_photovoltaic_total_energy(pv_inputdata):
    """全太陽光発電システムの年間一次エネルギー換算発電量を検証"""
    result = photovoltaic.calc_energy(pv_inputdata)
    assert result["E_photovoltaic"] == pytest.approx(EXPECTED_E_PV, rel=0.0001, abs=0.0001)


def test_photovoltaic_system_count(pv_inputdata):
    """太陽光発電システム数（19システム）を検証"""
    result = photovoltaic.calc_energy(pv_inputdata)
    assert len(result["PhotovoltaicSystems"]) == 19


def test_photovoltaic_slope_dependency(pv_inputdata):
    """傾斜角が大きくなると発電量が減少することを検証（90°以上で減少）"""
    result = photovoltaic.calc_energy(pv_inputdata)
    systems = list(result["PhotovoltaicSystems"].values())

    # システム03（傾斜20°）が最大発電量付近であることを確認
    ep_values = [s["Ep_kWh"] for s in systems]
    max_idx = ep_values.index(max(ep_values))
    assert 1 <= max_idx <= 5  # 傾斜10°〜50°の間で最大になるはず

    # 傾斜90°以降（システム10〜19）で発電量が減少することを確認
    assert systems[9]["Ep_kWh"] < systems[3]["Ep_kWh"]
    assert systems[18]["Ep_kWh"] < systems[9]["Ep_kWh"]


if __name__ == '__main__':
    pytest.main(["-v", __file__])
