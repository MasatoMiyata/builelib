import json
import pytest
import xlrd
from pathlib import Path

from builelib.systems import airconditioning_webpro
from builelib.systems import ventilation
from builelib.systems import lighting
from builelib.systems import hotwatersupply
from builelib.systems import elevator
from builelib.systems import photovoltaic
from builelib.systems import other_energy
from builelib.systems import cogeneration

# テストケースファイルのディレクトリ
TEST_DATA_DIR = Path(__file__).parent / "cogeneration"

# テストケースの定義
TEST_CASES = {
    "CGS_basic": "★CGSテストケース一覧.xlsx",
}

def read_testcasefile(filename):
    """テストケースファイルを読み込む関数"""
    wb = xlrd.open_workbook(filename)
    sheet = wb.sheet_by_name("Sheet1")
    # ヘッダーをスキップして読み込む
    testdata = [sheet.row_values(row) for row in range(1, sheet.nrows)]
    return testdata

def get_test_data():
    """テストデータを生成する"""
    test_to_try = []
    testcase_ids = []

    for case_name, filename in TEST_CASES.items():
        filepath = TEST_DATA_DIR / filename
        if not filepath.exists():
            continue

        # テストケース一覧の読み込み
        testfiledata = read_testcasefile(filepath)

        for row in testfiledata:
            json_filename = f"{row[0]}.json"
            json_filepath = TEST_DATA_DIR / json_filename
            
            if not json_filepath.exists():
                continue

            # 入力データの作成
            with open(json_filepath, 'r', encoding='utf-8') as f:
                inputdata = json.load(f)

            if "SpecialInputData" not in inputdata:
                inputdata["SpecialInputData"] = {}

            # 期待値
            expectedvalue = row[16]

            test_to_try.append((inputdata, expectedvalue))
            testcase_ids.append(f"{case_name}_{row[0]}")
            
    return test_to_try, testcase_ids

# テストデータの読み込み
test_data, test_ids = get_test_data()

@pytest.mark.parametrize("inputdata, expectedvalue", test_data, ids=test_ids)
def test_calc(inputdata, expectedvalue):
    # 各設備の計算結果格納用
    resultJson_for_CGS = {
        "AC": {},
        "V": {},
        "L": {},
        "HW": {},
        "EV": {},
        "PV": {},
        "OT": {},
    }

    # 各設備の計算実行
    if inputdata.get("AirConditioningZone"):
        resultJsonAC = airconditioning_webpro.calc_energy(inputdata)
        resultJson_for_CGS["AC"] = resultJsonAC["for_CGS"]
    if inputdata.get("VentilationRoom"):
        resultJsonV = ventilation.calc_energy(inputdata)
        resultJson_for_CGS["V"] = resultJsonV["for_CGS"]
    if inputdata.get("LightingSystems"):
        resultJsonL = lighting.calc_energy(inputdata)
        resultJson_for_CGS["L"] = resultJsonL["for_CGS"]
    if inputdata.get("HotwaterRoom"):
        resultJsonHW = hotwatersupply.calc_energy(inputdata)
        resultJson_for_CGS["HW"] = resultJsonHW["for_CGS"]
    if inputdata.get("Elevators"): 
        resultJsonEV = elevator.calc_energy(inputdata)
        resultJson_for_CGS["EV"] = resultJsonEV["for_CGS"]
    if inputdata.get("PhotovoltaicSystems"):
        resultJsonPV = photovoltaic.calc_energy(inputdata)
        resultJson_for_CGS["PV"] = resultJsonPV["for_CGS"]
    if inputdata.get("Rooms"):
        resultJsonOT = other_energy.calc_energy(inputdata)
        resultJson_for_CGS["OT"] = resultJsonOT["for_CGS"]

    # コージェネレーションの計算実行
    resultJson = cogeneration.calc_energy(inputdata, resultJson_for_CGS)

    # 比較（相対誤差0.01% または 絶対誤差0.0001）
    assert resultJson["年間一次エネルギー削減量"] == pytest.approx(expectedvalue, rel=0.0001, abs=0.0001)

if __name__ == '__main__':
    pytest.main(["-q", __file__])
