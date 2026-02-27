import pytest
from builelib.envelope import shading
from tests import test_utils

def load_test_cases(file_name):
    """
    テストケースをCSVファイルから読み込み、pytestで利用可能な形式に変換します。
    """
    test_cases = []
    
    # テストケースファイルの読み込み
    filename = test_utils.get_test_file_path(file_name)
    test_data = test_utils.read_csv(filename, encoding='utf-8-sig')
    
    # ヘッダーをスキップ
    header = test_data.pop(0)
    
    for row in test_data:
        case_id = row[0]
        area = row[1]
        direction = row[2]
        x1 = test_utils.convert2number(row[3], 0.0)
        x2 = test_utils.convert2number(row[4], 0.0)
        x3 = test_utils.convert2number(row[5], 0.0)
        y1 = test_utils.convert2number(row[6], 0.0)
        y2 = test_utils.convert2number(row[7], 0.0)
        y3 = test_utils.convert2number(row[8], 0.0)
        zxp = test_utils.convert2number(row[9], 0.0)
        zxm = test_utils.convert2number(row[10], 0.0)
        zyp = test_utils.convert2number(row[11], 0.0)
        zym = test_utils.convert2number(row[12], 0.0)
        
        error_expected = (row[13] == "ERR")
        
        expected_r_wind_sum = test_utils.convert2number(row[14], None)
        expected_r_wind_win = test_utils.convert2number(row[15], None)
        
        inputs = (area, direction, x1, x2, x3, y1, y2, y3, zxp, zxm, zyp, zym)
        expected = (expected_r_wind_sum, expected_r_wind_win)
        
        test_cases.append(pytest.param(inputs, expected, error_expected, id=case_id))

    return test_cases

@pytest.mark.parametrize("inputs, expected, error_expected", load_test_cases('shading/shading_test1.csv'))
def test_calc_shading_coefficient_1(inputs, expected, error_expected):
    """
    庇の効果係数の計算をテストします (shading_test1.csv)。
    """
    if not error_expected:
        # 計算の実行
        r_wind_sum, r_wind_win = shading.calc_shadingCoefficient(*inputs)
        
        # アサーション
        assert r_wind_sum == pytest.approx(expected[0], rel=1e-5)
        assert r_wind_win == pytest.approx(expected[1], rel=1e-5)
    else:
        # 例外のテスト
        with pytest.raises(Exception):
            shading.calc_shadingCoefficient(*inputs)

# @pytest.mark.parametrize("inputs, expected, error_expected", load_test_cases('shading/shading_test2.csv'))
# def test_calc_shading_coefficient_2(inputs, expected, error_expected):
#     """
#     庇の効果係数の計算をテストします (shading_test2.csv)。
#     実行に時間がかかるため注意
#     """
#     if not error_expected:
#         # 計算の実行
#         r_wind_sum, r_wind_win = shading.calc_shadingCoefficient(*inputs)
        
#         # アサーション
#         assert r_wind_sum == pytest.approx(expected[0], rel=1e-5)
#         assert r_wind_win == pytest.approx(expected[1], rel=1e-5)
#     else:
#         # 例外のテスト
#         with pytest.raises(Exception):
#             shading.calc_shadingCoefficient(*inputs)

if __name__ == '__main__':
    print('--- test_shading.py ---')
