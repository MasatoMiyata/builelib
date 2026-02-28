import pytest
from pathlib import Path
from builelib.systems import airconditioning_webpro
from tests.test_utils import read_excel, read_json

# テストケースファイルのディレクトリ
TEST_DATA_DIR = Path(__file__).parent / "airconditioning"

# テストケースの定義
TEST_CASES = {
    "AHU_basic": "★空調設備テストケース一覧.xlsx",
}


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
            case_id = row[0]
            json_path = TEST_DATA_DIR / f"ACtest_{case_id}.json"
            if not json_path.exists():
                continue

            inputdata = read_json(json_path)
            inputdata.setdefault("SpecialInputData", {})
            expectedvalue = row[4]

            test_to_try.append((inputdata, expectedvalue))
            testcase_ids.append(f"{case_name}_{case_id}")

    return test_to_try, testcase_ids


# テストデータの読み込み
test_data, test_ids = get_test_data()


@pytest.mark.parametrize("inputdata, expectedvalue", test_data, ids=test_ids)
def test_calc_airconditioning(inputdata, expectedvalue):
    resultJson = airconditioning_webpro.calc_energy(inputdata)
    assert resultJson["設計一次エネルギー消費量[MJ/年]"] == pytest.approx(expectedvalue, rel=0.0001, abs=0.0001)


if __name__ == '__main__':
    pytest.main(["-q", __file__])
