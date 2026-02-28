import pytest
from pathlib import Path
from builelib.systems import airconditioning_webpro
from tests.test_utils import convert2number, read_excel, read_json

# テストケースファイルのディレクトリ
TEST_DATA_DIR = Path(__file__).parent / "airconditioning_gshp_openloop"

# テストケースの定義
TEST_CASES = {
    "basic": "★地中熱クローズループ_テストケース一覧.xlsx",
}

# ベースとなる入力JSONファイル
BASE_JSON = TEST_DATA_DIR / "AC_gshp_closeloop_base.json"


def make_inputdata(row):
    """Excelの行データから入力データを作成する"""
    inputdata = read_json(BASE_JSON)
    inputdata.setdefault("SpecialInputData", {})
    inputdata["Building"]["Region"] = str(row[3]).replace("地域", "")
    inputdata["HeatsourceSystem"]["PAC1"]["冷房"]["Heatsource"][0]["HeatsourceType"] = row[1]
    inputdata["HeatsourceSystem"]["PAC1"]["暖房"]["Heatsource"][0]["HeatsourceType"] = row[2]
    return inputdata


def get_test_data():
    """テストデータを生成する"""
    test_to_try = []
    testcase_ids = []

    for case_name, filename in TEST_CASES.items():
        filepath = TEST_DATA_DIR / filename
        if not filepath.exists():
            continue

        testfiledata = read_excel(filepath)
        # ヘッダーをスキップ
        for row in testfiledata[1:]:
            inputdata = make_inputdata(row)
            expectedvalue = convert2number(row[4], 0)
            test_to_try.append((inputdata, expectedvalue))
            testcase_ids.append(f"{case_name}{row[0]}")

    return test_to_try, testcase_ids


# テストデータの読み込み
test_data, test_ids = get_test_data()


@pytest.mark.parametrize("inputdata, expectedvalue", test_data, ids=test_ids)
def test_calc(inputdata, expectedvalue):
    resultJson = airconditioning_webpro.calc_energy(inputdata)
    assert resultJson["設計一次エネルギー消費量[MJ/年]"] == pytest.approx(expectedvalue, rel=0.0001, abs=0.0001)


if __name__ == '__main__':
    pytest.main(["-q", __file__])
