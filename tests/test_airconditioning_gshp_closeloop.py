import pytest
from pathlib import Path
from builelib.input.make_inputdata import make_jsondata_from_Ver2_sheet
from builelib.systems import airconditioning_webpro
from tests.test_utils import convert2number, read_csv

# テストケースファイルのディレクトリ
TEST_DATA_DIR = Path(__file__).parent / "airconditioning_gshp_closeloop"

# 正解値ファイル（列4: 設計一次エネ[MJ/m2年], 列5: 基準一次エネ[MJ/m2年]）
# CSVには各Caseが1〜8地域の8行ずつ含まれる（計80行）
RESULTS_CSV = TEST_DATA_DIR / "Results.csv"


def get_test_data():
    """テストデータを生成する（10ケース × 8地域 = 80件）"""
    test_to_try = []
    testcase_ids = []

    if not RESULTS_CSV.exists():
        return test_to_try, testcase_ids

    rows = read_csv(RESULTS_CSV, encoding='shift-jis')

    for row in rows[1:]:
        case_id = row[0]       # 'Case01' など
        num = case_id[4:]      # '01' など
        region = row[1][0]     # 地域区分の先頭数字 ('1'〜'8')

        xlsm_path = TEST_DATA_DIR / f"Case_ac_gshp_closeloop_{num}.xlsm"
        if not xlsm_path.exists():
            continue

        expected_design = convert2number(row[4], 0)    # 設計一次エネルギー消費量[MJ/m2年]
        expected_standard = convert2number(row[5], 0)  # 基準一次エネルギー消費量[MJ/m2年]

        test_to_try.append((xlsm_path, region, expected_design, expected_standard))
        testcase_ids.append(f"{case_id}_Region{region}")

    return test_to_try, testcase_ids


# テストデータの読み込み
test_data, test_ids = get_test_data()


@pytest.mark.parametrize("xlsm_path, region, expected_design, expected_standard", test_data, ids=test_ids)
def test_calc(xlsm_path, region, expected_design, expected_standard):
    inputdata, _ = make_jsondata_from_Ver2_sheet(str(xlsm_path))
    inputdata.setdefault("SpecialInputData", {})
    inputdata["Building"]["Region"] = region

    resultJson = airconditioning_webpro.calc_energy(inputdata)

    actual_design = resultJson["設計一次エネルギー消費量[MJ/m2年]"]
    actual_standard = resultJson["基準一次エネルギー消費量[MJ/m2年]"]

    assert actual_design == pytest.approx(expected_design, rel=0.0001, abs=0.0001)
    assert actual_standard == pytest.approx(expected_standard, rel=0.0001, abs=0.0001)


if __name__ == '__main__':
    pytest.main(["-v", __file__])
